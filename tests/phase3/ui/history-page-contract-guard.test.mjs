import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {messages,conversations,HistoryFailure} from '../../../apps/web/src/history/client.ts';

const cases=JSON.parse(readFileSync(new URL(
  '../../../packages/contracts/fixtures/product.v1.cases.json',import.meta.url),'utf8')).cases;
function fixture(name){
  const c=cases.find(x=>x.case_id===name&&x.expected_valid);
  assert.ok(c,'Missing original product.v1 fixture '+name);
  return structuredClone(c.document);
}
async function withPage(page,run){
  const saved=globalThis.fetch;
  globalThis.fetch=async()=>new Response(JSON.stringify(page),{
    status:200,headers:{'content-type':'application/json'}});
  try{return await run();}finally{globalThis.fetch=saved;}
}
function historyMessages(first,second){
  const doc=fixture('valid_history_messages_page');
  const original=fixture('valid_user_message');
  doc.items=[{...original,message_id:'msg_z',created_at:first},
    {...original,message_id:'msg_a',created_at:second}];
  doc.page={limit:2,has_more:false,next_cursor:null};
  return doc;
}
function historyConversations(first,second){
  const doc=fixture('valid_paginated_conversations');
  const base=doc.items[0];
  doc.items=[{...base,conversation_id:'conv_a',created_at:first},
    {...base,conversation_id:'conv_z',created_at:second}];
  doc.page={limit:2,has_more:false,next_cursor:null};
  return doc;
}

const invalidError=e=>e instanceof HistoryFailure&&e.reason==='invalid';
const first='2026-01-01T00:00:00.123001Z',second='2026-01-01T00:00:00.123002Z';
for(const bad of ['2026-02-29T00:00:00Z','2026-02-30T00:00:00Z',
  '2026-04-31T00:00:00Z','2026-01-01T24:00:00Z',
  '1900-02-29T00:00:00Z','2026-02-30T01:00:00+01:00']){
  test('message calendar guard: '+bad,async()=>{
    const p=historyMessages(bad.startsWith('1900')?'1899-12-31T00:00:00Z':first,bad);
    await withPage(p,()=>assert.rejects(messages('conv_1',2),invalidError));
  });
}
test('conversation calendar guard rejects normalized April 31',async()=>{
  const p=historyConversations('2026-04-31T00:00:00Z',first);
  await withPage(p,()=>assert.rejects(conversations(2),invalidError));
});
test('real leap day with offset and microseconds remains valid',async()=>{
  const p=historyMessages('2024-02-29T01:00:00.123001+01:00',
    '2024-02-29T00:00:00.123002Z');
  const got=await withPage(p,()=>messages('conv_1',2));
  assert.deepEqual(got.items.map(x=>x.id),['msg_z','msg_a']);
});
test('century divisible by 400 remains valid',async()=>{
  const p=historyMessages('2000-02-29T00:00:00.123001Z',
    '2000-02-29T00:00:00.123002Z');
  const got=await withPage(p,()=>messages('conv_1',2));
  assert.equal(got.items.length,2);
});
// Explicit synthetic opaque tokens: the original valid fixture is terminal.
const cursor='fixture-cursor-page-2';
const alternate='fixture-cursor-page-1';
for(const [name,build,read] of [
  ['messages',()=>historyMessages(first,second),c=>messages('conv_1',2,c)],
  ['conversations',()=>historyConversations(second,first),c=>conversations(2,c)]]){
  test(name+' rejects self-loop cursor',async()=>{
    const p=build();p.page={limit:2,has_more:true,next_cursor:cursor};
    await withPage(p,()=>assert.rejects(read(cursor),invalidError));
  });
  test(name+' rejects nonterminal empty page',async()=>{
    const p=build();p.items=[];p.page={limit:2,has_more:true,next_cursor:cursor};
    await withPage(p,()=>assert.rejects(read(null),invalidError));
  });
  test(name+' accepts a progressing cursor',async()=>{
    const p=build();p.page={limit:2,has_more:true,next_cursor:cursor};
    const got=await withPage(p,()=>read(alternate));
    assert.equal(got.next,cursor);assert.equal(got.more,true);
  });
  test(name+' accepts an empty terminal page',async()=>{
    const p=build();p.items=[];p.page={limit:2,has_more:false,next_cursor:null};
    const got=await withPage(p,()=>read(cursor));
    assert.equal(got.items.length,0);assert.equal(got.more,false);
  });
}
