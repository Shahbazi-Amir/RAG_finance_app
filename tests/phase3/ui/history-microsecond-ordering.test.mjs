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
test('real PostgreSQL microseconds: message IDs need not sort lexically within the same millisecond',async()=>{
  const page=historyMessages('2026-01-01T00:00:00.123001Z',
                             '2026-01-01T00:00:00.123002Z');
  const got=await withPage(page,()=>messages('conv_1',2));
  assert.deepEqual(got.items.map(x=>x.id),['msg_z','msg_a']);
});
test('microsecond-reversed messages MUST fail, even when their IDs happen to sort',async()=>{
  const page=historyMessages('2026-01-01T00:00:00.123002Z',
                             '2026-01-01T00:00:00.123001Z');
  await withPage(page,()=>assert.rejects(messages('conv_1',2),e=>
    e instanceof HistoryFailure&&e.reason==='invalid'));
});
test('offset-aware microsecond message time is normalized to UTC instant',async()=>{
  const page=historyMessages('2026-01-01T01:00:00.123001+01:00',
                             '2026-01-01T00:00:00.123002Z');
  const got=await withPage(page,()=>messages('conv_1',2));
  assert.deepEqual(got.items.map(x=>x.id),['msg_z','msg_a']);
});
test('future precision > 6 digits cannot silently truncate a nonzero sub-microsecond',async()=>{
  const page=historyMessages('2026-01-01T00:00:00.1230011Z',
                             '2026-01-01T00:00:00.123002Z');
  await withPage(page,()=>assert.rejects(messages('conv_1',2),e=>
    e instanceof HistoryFailure&&e.reason==='invalid'));
});
test('conversation pages DESC preserve PostgreSQL microseconds independently of IDs',async()=>{
  const page=historyConversations('2026-01-01T00:00:00.123002Z',
                                  '2026-01-01T00:00:00.123001Z');
  const got=await withPage(page,()=>conversations(2));
  assert.deepEqual(got.items.map(x=>x.id),['conv_a','conv_z']);
});
test('conversation pages DESC reject microsecond reversed order',async()=>{
  const page=historyConversations('2026-01-01T00:00:00.123001Z',
                                  '2026-01-01T00:00:00.123002Z');
  await withPage(page,()=>assert.rejects(conversations(2),e=>
    e instanceof HistoryFailure&&e.reason==='invalid'));
});
