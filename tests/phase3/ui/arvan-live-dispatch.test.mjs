import assert from 'node:assert/strict';
import test from 'node:test';
import {
  decodeRuntimeCapability,selectRuntimeCapability
} from '../../../apps/web/src/ui/runtime-capability.ts';
import {recoverLiveResult} from '../../../apps/web/src/history/client.ts';

test('the v2 live capability is opt-in and remains blocked by app-only policy',()=>{
  const input={appOnly:false,approvedNoDispatch:false,ciFixture:false,approvedLive:true};
  const enabled=selectRuntimeCapability(input);
  assert.equal(enabled.send_mode,'LIVE_DISPATCH');
  assert.deepEqual(decodeRuntimeCapability(enabled),enabled);
  assert.equal(decodeRuntimeCapability({...enabled,contract_version:'ui.runtime_capabilities.v1'}),null);
  assert.equal(decodeRuntimeCapability({...enabled,generation_available:false}),null);
  assert.equal(selectRuntimeCapability({...input,appOnly:true}).send_mode,'DISABLED');
});

test('live result is a GET and checks the persisted attempt and trace',async t=>{
  const attempt='a'.repeat(32),trace='b'.repeat(32);
  const record={requested_conversation_id:null,client_message_id:'client',idempotency_key:'key12345'};
  const claims=[{text:'پاسخ',quote:'نقل‌قول',chunk_id:'chunk'}];
  t.mock.method(globalThis,'fetch',async (url,opts)=>{
    assert.match(url,/\/message-requests\/live-result\?requested_conversation_id=&client_message_id=client&idempotency_key=key12345$/);
    assert.equal(opts.method,'GET');
    return Response.json({kind:'arvan_staging_live_result',contract_version:'staging.arvan_live_result.v1',
      attempt_id:attempt,
      attempt_trace_id:trace,state:'READY',outcome:'ANSWER',claims});
  });
  assert.deepEqual(await recoverLiveResult(record,attempt,trace),{state:'READY',outcome:'ANSWER',claims});
  await assert.rejects(recoverLiveResult(record,attempt,'c'.repeat(32)),/invalid/);
});
