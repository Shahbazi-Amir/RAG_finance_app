import test from 'node:test';
import assert from 'node:assert/strict';
import {CHECKPOINT_KEY,readCheckpoints,retainCheckpoint,
  forgetCheckpoints,statusCorrelators} from '../../../apps/web/src/ui/attempt-checkpoints.ts';

function memory(){
  const data=new Map();
  return {getItem:k=>data.get(k)??null,
    setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)};
}
const item=(s='uih_aaaa')=>({
  requested_conversation_id:null,client_message_id:s,
  idempotency_key:'key_1234567890',created_at:1784301000000,
  resolved_conversation_id:null,
});
test('checkpoint before irreversible send preserves only original immutable correlators',()=>{
  const storage=memory(),r=item();
  assert.equal(retainCheckpoint(storage,r),true);
  const raw=storage.getItem(CHECKPOINT_KEY);
  assert.ok(raw.includes(r.client_message_id));
  for(const banned of ['question','answer_text','session','owner_user_id','cookie','token']){
    assert.equal(raw.includes(banned),false,banned);
  }
  assert.deepEqual(readCheckpoints(storage),[r]);
  assert.deepEqual(statusCorrelators(readCheckpoints(storage)[0]),{
    requested_conversation_id:null,client_message_id:r.client_message_id,
    idempotency_key:r.idempotency_key});
  assert.equal(retainCheckpoint(storage,{...r,requested_conversation_id:'conv_1'}),false);
  assert.equal(readCheckpoints(storage)[0].requested_conversation_id,null);
  assert.equal(retainCheckpoint(storage,{...r,resolved_conversation_id:'conv_1'}),true);
  assert.equal(readCheckpoints(storage)[0].resolved_conversation_id,'conv_1');
  forgetCheckpoints(storage);assert.deepEqual(readCheckpoints(storage),[]);
});
test('fails closed if browser refuses persistence, and corrupt/huge entries are discarded',()=>{
  const broken={getItem:()=>null,setItem:()=>{throw Error('Quota')},removeItem:()=>{}};
  assert.equal(retainCheckpoint(broken,item()),false);
  const storage=memory();
  storage.setItem(CHECKPOINT_KEY,'not-json');
  assert.deepEqual(readCheckpoints(storage),[]);
  storage.setItem(CHECKPOINT_KEY,JSON.stringify([{...item(),client_message_id:'<bad>'}]));
  assert.deepEqual(readCheckpoints(storage),[]);
  storage.setItem(CHECKPOINT_KEY,JSON.stringify(Array.from({length:49},(_,i)=>item('uih_'+i))));
  assert.deepEqual(readCheckpoints(storage),[]);
  assert.equal(retainCheckpoint(storage,item()),true);
  assert.equal(retainCheckpoint(storage,item('uih_other')),true);
});
test('no question, secret or user identity enters the checkpoint even after a status',()=>{
  const st=memory(),r=item('uih_second');
  assert.equal(retainCheckpoint(st,r),true);
  assert.equal(retainCheckpoint(st,{...r,resolved_conversation_id:'conv_confirmed'}),true);
  assert.deepEqual(Object.keys(readCheckpoints(st)[0]).sort(),
    ['client_message_id','created_at','idempotency_key',
     'requested_conversation_id','resolved_conversation_id'].sort());
});
