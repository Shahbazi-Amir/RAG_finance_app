import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
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

test('receipt user message is separate from assistant Answer.message_id; replay preserves both',async()=>{
  const t=new MockTransport(),req=newRequest('پرسش مستقل شناسه‌ها',null,'snapshot01');
  const first=await collect(t,req);
  const r=receipt(first),a=answer(first);
  assert.ok(a && r.message_id);
  assert.notEqual(r.message_id,a.message_id,'Receipt belongs to user, Answer to assistant');
  assert.match(r.message_id,/^msg_user_mock_/);
  assert.match(a.message_id,/^msg_assistant_mock_/);
  const replay=await collect(t,req);
  assert.equal(receipt(replay).disposition,'replayed');
  assert.equal(receipt(replay).message_id,r.message_id);
  assert.equal(answer(replay).message_id,a.message_id);
  assert.equal(answer(replay).answer_id,a.answer_id);
  assert.equal(receipt(replay).resolved_conversation_id,r.resolved_conversation_id);
  assert.notEqual(receipt(replay).trace_id,r.trace_id,'current retry attempt owns trace');

  // Reuse the shared contract's valid_snapshot_relations document shape;
  // do not create a parallel Wire Schema or pretend mock records are persisted.
  const registry=JSON.parse(readFileSync(new URL('../../../packages/contracts/fixtures/product.v1.cases.json',import.meta.url),'utf8'));
  const template=registry.cases.find(x=>x.case_id==='valid_snapshot_relations')?.document;
  assert.ok(template,'Snapshot fixture must exist in the UNCHANGED complete shared registry');
  const snapshot=structuredClone(template);
  snapshot.conversation.conversation_id=r.resolved_conversation_id;
  snapshot.conversation.owner_user_id=r.owner_user_id;
  const user={...snapshot.messages.find(m=>m.role==='user'),message_id:r.message_id,
    conversation_id:r.resolved_conversation_id,owner_user_id:r.owner_user_id,text:req.question,answer_id:null};
  const assistant={...snapshot.messages.find(m=>m.role==='assistant'),message_id:a.message_id,
    conversation_id:r.resolved_conversation_id,owner_user_id:r.owner_user_id,
    text:a.answer_text,answer_id:a.answer_id};
  snapshot.messages=[user,assistant];snapshot.answers=[a];snapshot.feedback=[];
  assert.equal(snapshot.kind,'conversation_snapshot');
  assert.equal(snapshot.messages.filter(m=>m.role==='user').length,1);
  assert.equal(snapshot.messages.filter(m=>m.role==='assistant').length,1);
  assert.equal(new Set(snapshot.messages.map(m=>m.message_id)).size,2);
  assert.equal(user.answer_id,null);
  assert.equal(assistant.answer_id,a.answer_id);
  assert.equal(a.message_id,assistant.message_id);
  assert.equal(a.conversation_id,snapshot.conversation.conversation_id);
  assert.ok(snapshot.messages.every(m=>m.owner_user_id===snapshot.conversation.owner_user_id));
  assert.deepEqual(a.claims.map(c=>c.citation_ids),[['cite_1']]);
  assert.deepEqual(a.citations[0].claim_ids,['claim_1']);
});
