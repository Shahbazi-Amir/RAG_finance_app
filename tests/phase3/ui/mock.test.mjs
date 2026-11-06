import test from 'node:test';
import assert from 'node:assert/strict';
import {MockTransport,newRequest,requestFingerprint,safeSourceHref,terminalDisplay} from '../../../apps/web/src/mock/transport.ts';
async function collect(t,r,s='answer'){const updates=[];for await(const u of t.send(r,s))updates.push(u);return updates}
const receipt=items=>items.find(x=>x.kind==='receipt').receipt;
const events=items=>items.filter(x=>x.kind==='event').map(x=>x.event);
const answer=items=>items.find(x=>x.kind==='answer')?.answer;

test('allocated thread and message replay exactly without duplicates',async()=>{
  const t=new MockTransport(),req=newRequest('سؤال مالی',null,'unique1');
  const first=receipt(await collect(t,req)),retry=receipt(await collect(t,req));
  assert.equal(first.disposition,'created');assert.equal(retry.disposition,'replayed');
  assert.equal(first.requested_conversation_id,null);assert.equal(retry.requested_conversation_id,null);
  assert.equal(first.message_id,retry.message_id);
  assert.equal(first.resolved_conversation_id,retry.resolved_conversation_id);
  assert.notEqual(first.trace_id,retry.trace_id);
  assert.equal(first.payload_sha256,await requestFingerprint(req));
});
test('changed original under same idempotency scope causes explicit conflict',async()=>{
  const t=new MockTransport(),r=newRequest('سلام',null,'conflict1');
  await collect(t,r);
  const updates=await collect(t,{...r,question:'تغییر متن'});
  assert.equal(receipt(updates).disposition,'conflict');
  assert.equal(receipt(updates).message_id,null);
  assert.equal(receipt(updates).resolved_conversation_id,null);
  assert.equal(receipt(updates).error.code,'IDEMPOTENCY_CONFLICT');
  assert.equal(events(updates).length,0);
});
test('delta whitespace and newlines are reconstructed unchanged',async()=>{
  const updates=await collect(new MockTransport(),newRequest('سؤال',null,'delta1'));
  const stream=events(updates);
  const chunks=stream.filter(e=>e.event_type==='delta').map(e=>e.data.text);
  assert.deepEqual(chunks,['این یک پاسخ',' ','آزمایشی است،','\n','نه پاسخ موتور واقعی.']);
  assert.equal(chunks.join(''),answer(updates).answer_text);
  assert.deepEqual(stream.map(e=>e.seq),Array.from({length:stream.length},(_,i)=>i));
  assert.equal(terminalDisplay(stream.at(-1)),'complete');
});
test('partial and no_answer/clarification/refusal are separate',async()=>{
  const t=new MockTransport();
  const partial=await collect(t,newRequest('سؤال',null,'p1'),'partial');
  assert.equal(answer(partial).outcome,'partial');
  assert.equal(terminalDisplay(events(partial).at(-1)),'partial');
  for(const outcome of ['no_answer','clarification','refusal']){
    const r=await collect(t,newRequest('سؤال',null,'s_'+outcome),outcome);
    assert.equal(answer(r).outcome,outcome);
    assert.equal(answer(r).claims.length,0);
  }
});
test('error and unknown do not resolve as complete answers',async()=>{
  for(const [scenario,expected] of [['error','failed'],['unknown','unknown']]){
    const r=await collect(new MockTransport(),newRequest('سؤال',null,'n_'+scenario),scenario);
    assert.equal(terminalDisplay(events(r).at(-1)),expected);
    assert.equal(answer(r),undefined);
  }
});
test('display-cancel is not proof of server stop; server requires ack',async()=>{
  const t=new MockTransport(),stream=t.send(newRequest('لغو',null,'cancel1'));
  await stream.next();
  const first=await stream.next();const id=first.value.event.request_id;
  assert.equal(first.value.event.event_type,'connected');
  t.requestServerCancellation(id);
  const more=[];for await(const x of stream)more.push(x);
  const last=events(more).at(-1);
  assert.equal(last.event_type,'server_cancelled');
  assert.equal(last.data.server_stopped,true);
  assert.equal(terminalDisplay(last),'server-cancelled');
  assert.equal(terminalDisplay({event_type:'display_cancelled',data:{effect:'display_only'}}),null);
});
test('malicious payload remains plain strings; unsafe hyperlinks rejected',async()=>{
  const r=await collect(new MockTransport(),newRequest('آزمایش',null,'bad1'),'malicious');
  const a=answer(r),s=a.citations[0].source;
  assert.match(a.answer_text,/<script>/);
  assert.match(s.display_title,/<svg/);
  assert.equal(s.attribution_status,'unknown');
  assert.equal(safeSourceHref(s),null);
  for(const url of ['javascript:alert(1)','data:text/html,<b>x</b>','http://example.com']){
    assert.equal(safeSourceHref({...s,resolution_status:'verified',locator:{kind:'url',url}}),null);
  }
});
