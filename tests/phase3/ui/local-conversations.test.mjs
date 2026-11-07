import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createWorkspace,openFreshThread,activeThread,selectThread,setThreadDraft,
  startItem,patchItem,attachResolvedConversation,setThreadScenario,threadPreview
} from '../../../apps/web/src/ui/local-conversations.ts';
import {newRequest,MockTransport} from '../../../apps/web/src/mock/transport.ts';

const local=id=>'local_ui_'+id;
const req=(question,conversationId=null,suffix='id')=>newRequest(question,conversationId,suffix);

test('repeated New Chat on an empty thread is idempotent, no fabricated history',()=>{
  let state=createWorkspace(()=>local('initial'));
  const first=state.activeId;
  for(let i=0;i<4;i++)state=openFreshThread(state,()=>local('different_'+i));
  assert.equal(state.threads.length,1);
  assert.equal(state.activeId,first);
  assert.equal(state.threads[0].items.length,0);
});

test('independent local IDs, original requested null, separate persisted IDs',()=>{
  let state=createWorkspace(()=>local('A'));
  const requestA=req('پرسش اول',null,'a');
  state=startItem(state,local('A'),requestA,'answer');
  state=attachResolvedConversation(state,local('A'),'conv_mock_A');
  state=openFreshThread(state,()=>local('B'));
  assert.deepEqual(state.threads.map(t=>t.localId),[local('A'),local('B')]);
  assert.equal(state.activeId,local('B'));
  const requestB=req('پرسش دوم',activeThread(state).resolvedConversationId,'b');
  assert.equal(requestB.requested_conversation_id,null);
  assert.notEqual(local('B'),requestB.requested_conversation_id);
  state=startItem(state,local('B'),requestB,'answer');
  state=attachResolvedConversation(state,local('B'),'conv_mock_B');
  assert.equal(state.threads[0].resolvedConversationId,'conv_mock_A');
  assert.equal(state.threads[1].resolvedConversationId,'conv_mock_B');
  assert.notEqual(state.threads[0].resolvedConversationId,state.threads[1].resolvedConversationId);
  // A follow-on request uses its own resolved ID, never local_ui_B.
  assert.equal(req('بعدی',state.threads[1].resolvedConversationId,'c').requested_conversation_id,'conv_mock_B');
});

test('switching threads preserves two drafts, messages, scenario, and active selection',()=>{
  let state=createWorkspace(()=>local('A'));
  state=setThreadDraft(state,local('A'),'پیش‌نویس اول');
  state=startItem(state,local('A'),req('پرسش اول',null,'one'),'answer');
  state=openFreshThread(state,()=>local('B'));
  state=setThreadDraft(state,local('B'),'پیش‌نویس دوم\nبا سطر تازه');
  state=setThreadScenario(state,local('B'),'partial');
  state=selectThread(state,local('A'));
  assert.equal(activeThread(state).draft,'پیش‌نویس اول');
  assert.equal(activeThread(state).items.length,1);
  state=selectThread(state,local('B'));
  assert.equal(activeThread(state).draft,'پیش‌نویس دوم\nبا سطر تازه');
  assert.equal(activeThread(state).scenario,'partial');
  assert.equal(activeThread(state).items.length,0);
  assert.equal(state.threads[0].items.length,1);
  assert.equal(threadPreview(state.threads[0]),'پرسش اول');
  assert.equal(selectThread(state,local('does_not_exist')),state);
});

test('late delta and receipt always update their originating thread after navigation',()=>{
  let state=createWorkspace(()=>local('A'));
  const msgA=req('متن A',null,'streamA');
  state=startItem(state,local('A'),msgA,'answer');
  state=openFreshThread(state,()=>local('B'));
  const msgB=req('متن B',null,'streamB');
  state=startItem(state,local('B'),msgB,'answer');
  // While B is active, A receives a delayed event and its server receipt.
  state=patchItem(state,local('A'),msgA.client_message_id,
    {phase:'delta',text:'بخش اول'+' '+'\n'+'بخش دوم'});
  state=attachResolvedConversation(state,local('A'),'conv_mock_10');
  assert.equal(activeThread(state).localId,local('B'));
  assert.equal(activeThread(state).items[0].text,'');
  assert.equal(state.threads[0].items[0].text,'بخش اول \nبخش دوم');
  assert.equal(state.threads[0].resolvedConversationId,'conv_mock_10');
  assert.equal(state.threads[1].resolvedConversationId,null);
  // Requested cancellation for B is not confirmed cancellation for A.
  state=patchItem(state,local('B'),msgB.client_message_id,
    {phase:'cancel-requested',cancelRequested:true});
  assert.equal(state.threads[0].items[0].cancelRequested,false);
  assert.equal(state.threads[0].items[0].terminal,undefined);
  assert.equal(state.threads[1].items[0].cancelRequested,true);
});

test('Mock server streams belonging to two local threads do not intermingle',async()=>{
  const transport=new MockTransport();
  let state=createWorkspace(()=>local('A'));
  const requestA=req('پرسش A',null,'stream_a_2');
  state=startItem(state,local('A'),requestA,'answer');
  const streamA=transport.send(requestA,'answer');
  const firstA=await streamA.next();
  assert.equal(firstA.value.kind,'receipt');
  state=attachResolvedConversation(state,local('A'),firstA.value.receipt.resolved_conversation_id);
  // Switch to B before A finishes, then run B independently.
  state=openFreshThread(state,()=>local('B'));
  const requestB=req('پرسش B',null,'stream_b_2');
  state=startItem(state,local('B'),requestB,'partial');
  const collect=async(localId,key,stream)=>{
    let text='';
    for await(const item of stream){
      if(item.kind==='event'&&item.event.event_type==='delta'){
        text+=item.event.data.text;
        state=patchItem(state,localId,key,{text,phase:'delta'});
      }else if(item.kind==='answer'){
        state=patchItem(state,localId,key,{answer:item.answer,terminal:item.answer.state,
          isRunning:false});
      }
    }
  };
  await Promise.all([
    collect(local('A'),requestA.client_message_id,streamA),
    collect(local('B'),requestB.client_message_id,transport.send(requestB,'partial'))
  ]);
  const [a,b]=state.threads;
  assert.equal(state.activeId,local('B'));
  assert.match(a.items[0].text,/نه پاسخ موتور واقعی/);
  assert.match(b.items[0].text,/ناقض|ناقص/);
  assert.notEqual(a.items[0].request.client_message_id,b.items[0].request.client_message_id);
  assert.equal(a.items[0].terminal,'completed');
  assert.equal(b.items[0].terminal,'partial');
  assert.notEqual(a.items[0].answer.message_id,b.items[0].answer.message_id);
});

test('New Chat preserves an unsent draft in its own selectable local thread',()=>{
  let state=createWorkspace(()=>local('draftA'));
  state=setThreadDraft(state,local('draftA'),'هنوز ارسال نشده\nولی باید حفظ شود');
  state=openFreshThread(state,()=>local('draftB'));
  assert.equal(state.threads.length,2);
  assert.equal(state.activeId,local('draftB'));
  assert.equal(activeThread(state).draft,'');
  state=openFreshThread(state,()=>local('no_duplicate'));
  assert.equal(state.threads.length,2);
  state=selectThread(state,local('draftA'));
  assert.equal(activeThread(state).draft,'هنوز ارسال نشده\nولی باید حفظ شود');
});
