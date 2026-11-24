'use client';
import {useCallback,useEffect,useRef,useState,type FormEvent} from 'react';
import Link from 'next/link';
import {conversations,messages,newSend,sendMessage,recoverStatus,recoverEngineStatus,recoverRetrievedSources,HistoryFailure,
  failureLabel,mergeUnique,type ConversationView,type MessageView,
  type AnswerView,type HistoryStatus,type EngineStatus,type RetrievedSources} from '../history/client';
import type {Answer,Citation} from '../mock/transport';
import {verifiedSourceUrl,verifiedSourceLocatorLabel,verifiedSourceTypeLabel} from './source-locator';
import {sourceCredits,confidenceLabel} from './source-metadata';
import RetrievedSourcesPanel from './retrieved-sources-panel';
import {OwnerFence} from './owner-fence';
import {isVerifiedLiveAnswer,productOutcomeLabel} from './answer-visibility';
import {blockedCapability,decodeRuntimeCapability,type RuntimeCapability} from './runtime-capability';
import {readCheckpoints,retainCheckpoint,forgetCheckpoints,statusCorrelators,
  type AttemptCheckpoint} from './attempt-checkpoints';

type ListData={items:ConversationView[];next:string|null;more:boolean};
type ThreadData={items:MessageView[];answers:AnswerView[];next:string|null;more:boolean};
type Attempt= {record:AttemptCheckpoint;viewId:string;question:string|null;phase:HistoryStatus|'sending'|'transport_unknown'|'invalid_answer'|'status_error';
  attemptId:string|null;messageId:string|null;answer:Answer|null;confirmed:boolean;
  engine:EngineStatus|null;engineUnavailable:boolean;
  sources:RetrievedSources|null;sourcesUnavailable:boolean};
const isTerminal=(phase:Attempt['phase'])=>
  ['answer_committed','invalid_answer','failed','cancelled'].includes(phase);
function phaseLabel(attempt:Attempt):string {
  switch(attempt.phase){
    case 'sending':return 'در حال ثبت پرسش…';
    case 'persisted':return 'پرسش ثبت شد؛ در انتظار شروع Attempt.';
    case 'attempt_pending':return 'در حال پردازش؛ وضعیت از API دریافت شده است.';
    case 'attempt_unknown':return 'نتیجهٔ Attempt نامعلوم است؛ ارسال مجدد انجام نمی‌شود.';
    case 'not_found':return 'هنوز رسیدی پیدا نشده؛ نتیجهٔ ارسال نامعلوم است.';
    case 'failed':return 'پردازش با خطای فنی پایان یافته است.';
    case 'cancelled':return 'لغو پردازش توسط سرور ثبت شده است.';
    case 'invalid_answer':return 'پاسخ نمونه یا تأییدنشده دریافت شده؛ در محصول نمایش داده نمی‌شود.';
    case 'answer_committed':return 'پاسخ تأییدشدهٔ همین Attempt دریافت شد.';
    case 'status_error':return 'خواندن وضعیت ناموفق بود؛ نتیجه نامعلوم است.';
    default:return 'ارتباط قطع شد؛ نتیجه نامعلوم است. فقط وضعیت پیگیری می‌شود.';
  }
}
function engineLabel(s:EngineStatus):string{
  switch(s.state){
    case 'NOT_STARTED':return 'اجرای فنی هنوز آغاز نشده است.';
    case 'NOT_RECORDED':return 'وضعیت فنی برای این Attempt ثبت نشده است.';
    case 'QUEUED':return 'در صف پردازش فنی بدون تولید پاسخ.';
    case 'RUNNING':return 'بازیابی شواهد در حال اجراست؛ تولید پاسخ غیرفعال است.';
    case 'CONTEXT_READY':return 'بازیابی شواهد کامل شد؛ تولید پاسخ انجام نشده است.';
    case 'FAILED':return 'پردازش فنی بدون تولید پاسخ با خطا پایان یافت.';
    default:return 'نتیجهٔ اجرای فنی نامعلوم است؛ ارسال مجدد انجام نمی‌شود.';
  }
}
function CitationView({citation}:{citation:Citation}){
  const s=citation.source;
  const href=verifiedSourceUrl(s);
  const locatorLabel=verifiedSourceLocatorLabel(s);
  const sourceTypeLabel=verifiedSourceTypeLabel(s);
  const credits=sourceCredits(s);
  return <li className="product-citation">
    {sourceTypeLabel&&<span>نوع منبع: {sourceTypeLabel}</span>}
    <span>شناسهٔ منبع: <code dir="ltr">{s.source_id??'ثبت نشده'}</code></span>
    {s.display_title&&s.display_title_origin!=='SYNTHETIC'&&
      <span>عنوان: {s.display_title}</span>}
    {credits.map(c=><span key={c.role}>{c.label}: {c.name}</span>)}
    {s.attribution_status!=='verified'&&<span className="history-note">انتساب این منبع تأیید نشده است.</span>}
    <span>شناسهٔ استناد: <code dir="ltr">{citation.citation_id}</code></span>
    <span>نقل‌قول مستقیم منبع: در این قرارداد ارائه نشده است.</span>
    {locatorLabel&&<span data-testid="verified-source-locator">{locatorLabel}</span>}
    {href?<a href={href} target="_blank" rel="noopener noreferrer">بازکردن پیوند معتبر منبع</a>
      :<span className="history-note">این نشانگر آدرس وب تأییدشده ندارد؛ امکان بازکردن پیوند وجود ندارد.</span>}
    <span className="history-note">دلیل انتخاب این منبع در قرارداد فعلی ارائه نشده است.</span>
  </li>;
}
function AnswerPanel({answer}:{answer:Answer}){
  if(!isVerifiedLiveAnswer(answer))return <p role="status" className="history-note">
    پاسخ نمونه یا تأییدنشده از API دریافت شده و عمداً نمایش داده نمی‌شود.
  </p>;
  return <div className="product-answer" data-testid={'answer-'+answer.answer_id}>
    {answer.answer_text&&<p className="history-message-text">{answer.answer_text}</p>}
    {productOutcomeLabel(answer)&&<p role="status" className="history-note">{productOutcomeLabel(answer)}</p>}
    <p className="history-note" data-testid="answer-confidence">{confidenceLabel(answer)}</p>
    {answer.claims.length>0&&<section aria-label="شواهد این پاسخ" className="product-evidence">
      <h2>شواهد همین پاسخ</h2>
      {answer.claims.map(claim=><div key={claim.claim_id} className="product-claim">
        <p>{claim.text}</p>
        <ul>{answer.citations.filter(c=>claim.citation_ids.includes(c.citation_id))
          .map(c=><CitationView key={c.citation_id} citation={c}/>)}</ul>
      </div>)}
    </section>}
    <p className="history-note">شناسهٔ پاسخ: <code>{answer.answer_id}</code></p>
  </div>;
}

// Storage access is optional. Sending requires checkpoint persistence first.
function sessionStore():Storage|null{
  try{return window.sessionStorage;}catch{return null;}
}
export default function ProductChat(){
  const [list,setList]=useState<ListData>({items:[],next:null,more:false});
  const [listState,setListState]=useState<'loading'|'ready'|'error'|'unauthorized'>('loading');
  const [selected,setSelected]=useState<string>('draft:new');
  const [drafts,setDrafts]=useState<Record<string,string>>({});
  const [threads,setThreads]=useState<Record<string,ThreadData>>({});
  const [attempts,setAttempts]=useState<Record<string,Attempt>>({});
  const [error,setError]=useState('');
  const [mobileOpen,setMobileOpen]=useState(false);
  const mobileMenu=useRef<HTMLElement|null>(null);
  const menuTrigger=useRef<HTMLButtonElement|null>(null);
  const [busy,setBusy]=useState(false);
  const [runtimeCapability,setRuntimeCapability]=useState<RuntimeCapability>(blockedCapability());
  const [capabilityState,setCapabilityState]=useState<'loading'|'ready'|'unavailable'>('loading');
  const canSend=capabilityState==='ready'&&runtimeCapability.send_mode==='NO_DISPATCH_ONLY';
  const lost=useRef(false);
  // Never mix a former account's in-flight History with a new owner's page.
  const ownerFence=useRef(new OwnerFence());
  const sending=useRef(false);
  const polling=useRef(new Set<string>());
  const attemptsRef=useRef(attempts);
  const threadEpochs=useRef<Record<string,number>>({});
  const listEpoch=useRef(0);
  // Monotonic privacy generation: any in-flight History/Attempt GET from
  // before a 503/401 owner revalidation must never update a newer view.
  const privacyEpoch=useRef(0);
  const restoreQueue=useRef<AttemptCheckpoint[]>([]);
  useEffect(()=>{attemptsRef.current=attempts},[attempts]);
  useEffect(()=>{
    let active=true;
    let generation=0;
    const load=async()=>{
      const current=++generation;
      try{
        const response=await fetch('/api/product-capabilities',{
          method:'GET',credentials:'same-origin',cache:'no-store'
        });
        if(!response.ok)throw new Error('CAPABILITY_UNAVAILABLE');
        const decoded=decodeRuntimeCapability(await response.json());
        if(!decoded)throw new Error('CAPABILITY_INVALID');
        if(!active||current!==generation)return;
        setRuntimeCapability(decoded);setCapabilityState('ready');
      }catch{
        if(!active||current!==generation)return;
        // Never reuse a previously permitted mode after capability outage.
        setRuntimeCapability(blockedCapability());setCapabilityState('unavailable');
      }
    };
    const refresh=()=>{if(document.visibilityState==='visible')void load();};
    void load();
    window.addEventListener('focus',refresh);
    document.addEventListener('visibilitychange',refresh);
    return ()=>{
      active=false;generation++;
      window.removeEventListener('focus',refresh);
      document.removeEventListener('visibilitychange',refresh);
    };
  },[]);
  const invalidate=useCallback((e:unknown):boolean=>{
    if(!(e instanceof HistoryFailure&&e.reason==='unauthorized'))return false;
    lost.current=true;
    ownerFence.current.invalidate();
    const s=sessionStore();if(s)forgetCheckpoints(s);
    attemptsRef.current={};
    threadEpochs.current={};
    listEpoch.current++;
    privacyEpoch.current++;
    setAttempts({});setList({items:[],next:null,more:false});
    setThreads({});setSelected('draft:new');setDrafts({});
    setListState('unauthorized');setError('');setMobileOpen(false);setBusy(false);
    return true;
  },[]);
  const matchOwner=useCallback((owner:string):boolean=>{
    if(ownerFence.current.observe(owner))return true;
    invalidate(new HistoryFailure(401,'unauthorized'));
    return false;
  },[invalidate]);
  const loadList=useCallback(async (append=false,cursor:string|null=null)=>{
    if(lost.current)return;
    const epoch=++listEpoch.current;
    try{
      // Keep the existing #49 browser A/B harness query `limit=2` stable.
      const page=await conversations(2,append?cursor:null);
      if(lost.current||!matchOwner(page.owner)||listEpoch.current!==epoch)return;
      setList(prev=>({items:append?mergeUnique(prev.items,page.items,x=>x.id):page.items,
        next:page.next,more:page.more}));
      setListState('ready');
      if(!append)setSelected(current=>current==='draft:new'&&page.items.length?
        page.items[0].id:current);
    }catch(e){
      if(invalidate(e)||lost.current)return;
      if(listEpoch.current!==epoch)return;
      // An invalid owner-bearing page cannot safely coexist with a prior
      // owner's visible messages, composer and checkpoint correlations.
      if(e instanceof HistoryFailure&&e.reason==='invalid'){
        invalidate(new HistoryFailure(401,'unauthorized'));return;
      }
      setList({items:[],next:null,more:false});
      // An unavailable owner revalidation cannot attest to the cached
      // conversation's identity. Hide messages immediately, retaining
      // only GET-only non-secret checkpoint state for a later valid owner.
      privacyEpoch.current++;
      threadEpochs.current={};
      setThreads({});
      setListState('error');setError(failureLabel(e));
    }
  },[invalidate,matchOwner]);
  const loadThread=useCallback(async (id:string,append=false,cursor:string|null=null)=>{
    if(lost.current||id.startsWith('draft:'))return;
    const epoch=(threadEpochs.current[id]??0)+1;
    const privacyAtStart=privacyEpoch.current;
    threadEpochs.current[id]=epoch;
    try{
      const page=await messages(id,30,append?cursor:null);
      if(lost.current||privacyEpoch.current!==privacyAtStart||
         threadEpochs.current[id]!==epoch||!matchOwner(page.owner))return;
      setThreads(all=>{
        if(privacyEpoch.current!==privacyAtStart)return all;
        const prev=all[id];
        return {...all,[id]:{
          items:append&&prev?mergeUnique(prev.items,page.items,x=>x.id):page.items,
          answers:append&&prev?mergeUnique(prev.answers,page.answers,x=>x.id):page.answers,
          next:page.next,more:page.more
        }};
      });
    }catch(e){
      if(privacyEpoch.current!==privacyAtStart)return;
      if(invalidate(e)||lost.current)return;
      if(threadEpochs.current[id]!==epoch)return;
      if(e instanceof HistoryFailure&&e.reason==='invalid'){
        invalidate(new HistoryFailure(401,'unauthorized'));return;
      }
      setThreads(all=>{const next={...all};delete next[id];return next;});
      setError(failureLabel(e));
    }
  },[invalidate,matchOwner]);
  const probe=useCallback(async (record:AttemptCheckpoint)=>{
    if(lost.current||polling.current.has(record.client_message_id))return;
    const privacyAtStart=privacyEpoch.current;
    polling.current.add(record.client_message_id);
    try{
      const status=await recoverStatus(statusCorrelators(record));
      if(lost.current||privacyEpoch.current!==privacyAtStart)return;
      const old=attemptsRef.current[record.client_message_id];
      if(old?.attemptId&&status.attemptId&&old.attemptId!==status.attemptId){
        setAttempts(all=>privacyEpoch.current!==privacyAtStart?all:{...all,[record.client_message_id]:{
          ...all[record.client_message_id],phase:'status_error',
          sources:null,sourcesUnavailable:true,engine:null,engineUnavailable:true,
          answer:null,attemptId:null,messageId:null}});
        return;
      }
      const resultPhase=status.status==='answer_committed'&&!isVerifiedLiveAnswer(status.answer)
        ?'invalid_answer':status.status;
      let technical:EngineStatus|null=null;
      let engineUnavailable=false;
      if(status.status!=='not_found'){
        try{
          technical=await recoverEngineStatus(statusCorrelators(record));
          if(technical&&status.attemptId&&technical.attemptId&&
             (technical.attemptId!==status.attemptId||
              (status.attemptTraceId!==null&&
               technical.attemptTraceId!==status.attemptTraceId)))
            throw new HistoryFailure(0,'invalid');
        }catch(e){
          if(privacyEpoch.current!==privacyAtStart)return;
          if(invalidate(e)||lost.current)return;
          engineUnavailable=true;
        }
      }
      let sources:RetrievedSources|null=null;
      let sourcesUnavailable=false;
      if(status.status!=='not_found'&&status.attemptId!==null){
        try{
          sources=await recoverRetrievedSources(statusCorrelators(record));
          if(sources&&(sources.attemptId!==status.attemptId||
             sources.attemptTraceId!==status.attemptTraceId))
            throw new HistoryFailure(0,'invalid');
        }catch(e){
          if(privacyEpoch.current!==privacyAtStart)return;
          if(invalidate(e)||lost.current)return;
          sourcesUnavailable=true;
        }
      }
      if(lost.current||privacyEpoch.current!==privacyAtStart)return;
      setAttempts(all=>{
        if(privacyEpoch.current!==privacyAtStart)return all;
        const previous=all[record.client_message_id];
        if(!previous||isTerminal(previous.phase))return all;
        return {...all,[record.client_message_id]:{
          ...previous,phase:resultPhase,attemptId:status.attemptId??previous.attemptId,
          messageId:status.messageId,answer:status.answer,
          engine:technical,engineUnavailable,
          sources,sourcesUnavailable,
          record:status.id?{...previous.record,resolved_conversation_id:status.id}:previous.record,
          viewId:status.id??previous.viewId,
          confirmed:status.status!=='not_found'
        }};
      });
      const confirmedId=status.id;
      if(privacyEpoch.current!==privacyAtStart)return;
      if(confirmedId&&status.status!=='not_found'){
        const s=sessionStore();if(s)retainCheckpoint(s,{...record,resolved_conversation_id:confirmedId});
        setSelected(old=>old.startsWith('draft:')?confirmedId:old);
        void loadList();
        void loadThread(confirmedId);
      }
    }catch(e){
      if(privacyEpoch.current!==privacyAtStart)return;
      if(!invalidate(e)&&!lost.current)
        setAttempts(all=>{
          const prev=all[record.client_message_id];
          return prev&&!isTerminal(prev.phase)?{...all,[record.client_message_id]:
            {...prev,phase:'status_error',answer:null,engine:null,engineUnavailable:true,
               sources:null,sourcesUnavailable:true,attemptId:null,messageId:null}}:all;
        });
    }finally{polling.current.delete(record.client_message_id);}
  },[invalidate,loadList,loadThread]);
  useEffect(()=>{
    let active=true;
    queueMicrotask(()=>{
      if(!active)return;
      const s=sessionStore();
      const saved=s?readCheckpoints(s):[];
      setAttempts(all=>{
        const next={...all};
        for(const record of saved)if(!next[record.client_message_id])
          next[record.client_message_id]={
            record,viewId:record.resolved_conversation_id??
              record.requested_conversation_id??'draft:new',
            question:null,phase:'transport_unknown',
            attemptId:null,messageId:null,answer:null,confirmed:false,
            engine:null,engineUnavailable:false,
            sources:null,sourcesUnavailable:false};
        return next;
      });
      restoreQueue.current=saved;
      void loadList();
    });
    return ()=>{active=false;};
  },[loadList]);
  useEffect(()=>{
    // A saved correlation has no authorization power and contains no owner.
    // Do not issue any recovery GET until the signed BFF conversation page
    // establishes a valid, consistent current owner.
    if(listState!=='ready'||lost.current)return;
    const saved=restoreQueue.current;
    restoreQueue.current=[];
    for(const record of saved)void probe(record);
  },[listState,probe]);
  useEffect(()=>{
    if(listState!=='ready'||!selected||selected.startsWith('draft:'))return;
    let active=true;
    // Load thread only after a signed owner-scoped list revalidates. A
    // recovered GET must fetch the same conversation again, not reveal a
    // cached thread from before the temporary identity outage.
    queueMicrotask(()=>{
      if(active)void loadThread(selected);
    });
    return ()=>{active=false;};
  },[selected,loadThread,listState]);
  useEffect(()=>{
    // A read-only identity heartbeat detects a revoked session or account
    // rotation even when no Attempt is pending. It never dispatches C018.
    const refresh=()=>{if(!lost.current&&document.visibilityState==='visible')
      void loadList();};
    const timer=window.setInterval(refresh,15000);
    window.addEventListener('focus',refresh);
    document.addEventListener('visibilitychange',refresh);
    return ()=>{
      window.clearInterval(timer);
      window.removeEventListener('focus',refresh);
      document.removeEventListener('visibilitychange',refresh);
    };
  },[loadList]);
  useEffect(()=>{
    if(!mobileOpen)return;
    const nav=mobileMenu.current;
    const trigger=menuTrigger.current;
    const close=nav?.querySelector<HTMLButtonElement>('.history-mobile-close');
    close?.focus();
    const desktop=window.matchMedia('(min-width: 761px)');
    const onDesktop=()=>{if(desktop.matches)setMobileOpen(false);};
    desktop.addEventListener('change',onDesktop);
    const onKeys=(event:KeyboardEvent)=>{
      if(event.key==='Escape'){event.preventDefault();setMobileOpen(false);return;}
      if(event.key!=='Tab'||!nav)return;
      const focusables=Array.from(nav.querySelectorAll<HTMLElement>(
        'button:not([disabled]),a[href]')).filter(el=>el.getClientRects().length>0);
      if(!focusables.length)return;
      const first=focusables[0],last=focusables[focusables.length-1];
      // A programmatic focus escape must not expose the background to
      // keyboard or assistive-tech users while the modal drawer is active.
      if(!nav.contains(document.activeElement)){
        event.preventDefault();(event.shiftKey?last:first).focus();return;
      }
      if(event.shiftKey&&document.activeElement===first){
        event.preventDefault();last.focus();
      }else if(!event.shiftKey&&document.activeElement===last){
        event.preventDefault();first.focus();
      }
    };
    window.addEventListener('keydown',onKeys);
    return ()=>{
      window.removeEventListener('keydown',onKeys);
      desktop.removeEventListener('change',onDesktop);
      if(trigger?.getClientRects().length)trigger.focus();
      else document.getElementById('product-main')?.focus();
    };
  },[mobileOpen]);
  useEffect(()=>{
    const timer=window.setInterval(()=>{
      if(lost.current||listState!=='ready'||document.visibilityState==='hidden')return;
      for(const attempt of Object.values(attemptsRef.current)){
        if(!isTerminal(attempt.phase))void probe(attempt.record);
      }
    },4500);
    return ()=>window.clearInterval(timer);
  },[probe,listState]);
  function newConversation(){
    if(lost.current||listState!=='ready'||!canSend)return;
    const id='draft:'+crypto.randomUUID();
    setSelected(id);setDrafts(all=>({...all,[id]:''}));setMobileOpen(false);
  }
  async function submit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();
    if(lost.current||sending.current||listState!=='ready'||!canSend)return;
    const question=(drafts[selected]??'').trim();
    if(!question)return;
    // A draft is a UI-only ID. The API allocates a real conversation on T1.
    const original=selected.startsWith('draft:')?null:selected;
    // Only a prior unresolved Send in the SAME persisted conversation
    // blocks a second send. An unrelated fresh draft may start independently.
    if(original!==null&&Object.values(attemptsRef.current).some(a=>
        !isTerminal(a.phase)&&
        (a.record.resolved_conversation_id??a.record.requested_conversation_id)===original))
      return;
    const request=newSend(question,original);
    const record:AttemptCheckpoint={
      requested_conversation_id:request.requested_conversation_id,
      client_message_id:request.client_message_id,idempotency_key:request.idempotency_key,
      created_at:Date.now(),resolved_conversation_id:null};
    const s=sessionStore();
    if(!s||!retainCheckpoint(s,record)){
      setError('این مرورگر امکان ذخیرهٔ شناسهٔ پیگیری را ندارد؛ پرسش ارسال نشد.');
      return;
    }
    sending.current=true;setBusy(true);setError('');
    setDrafts(all=>({...all,[selected]:''}));
    const attempt:Attempt={record,viewId:selected,question,phase:'sending',attemptId:null,
      messageId:null,answer:null,confirmed:false,engine:null,engineUnavailable:false,
      sources:null,sourcesUnavailable:false};
    attemptsRef.current={...attemptsRef.current,[record.client_message_id]:attempt};
    setAttempts(all=>({...all,[record.client_message_id]:attempt}));
    try{
      const receipt=await sendMessage(request); // exactly one POST per user action
      if(lost.current)return;
      setAttempts(all=>{const prev=all[record.client_message_id];return prev?
        {...all,[record.client_message_id]:{
          ...prev,
          // A status GET may finish before the delayed POST receipt.
          // The receipt cannot downgrade completed/unknown/failed outcome.
          phase:prev.phase==='sending'?'persisted':prev.phase,
          record:{...prev.record,resolved_conversation_id:receipt.id},
          viewId:receipt.id,messageId:receipt.messageId,confirmed:true}}:all;});
      retainCheckpoint(s,{...record,resolved_conversation_id:receipt.id});
      setSelected(old=>old===selected?receipt.id:old);
      void loadList();void loadThread(receipt.id);
      void probe(record); // GET only
    }catch(e){
      if(invalidate(e)||lost.current)return;
      setAttempts(all=>{const prev=all[record.client_message_id];return prev?
        {...all,[record.client_message_id]:{...prev,phase:'transport_unknown'}}:all;});
      setError(e instanceof HistoryFailure&&e.reason==='conflict'?
        'تعارض شناسهٔ ارسال؛ درخواست جدیدی ارسال نمی‌شود.':failureLabel(e));
    }finally{sending.current=false;setBusy(false);}
  }
  // Cached messages and attempt observations are invisible whenever the
  // currently authenticated owner cannot be revalidated.
  const verifiedPage=listState==='ready';
  const messagesFor=verifiedPage?threads[selected]:undefined;
  const renderedIds=new Set(messagesFor?.items.map(m=>m.id)??[]);
  const answers=new Map((messagesFor?.answers??[]).map(a=>[a.messageId,a.payload]));
  const selectedAttempts=verifiedPage?Object.values(attempts).filter(a=>a.viewId===selected):[];
  const pendingDrafts=verifiedPage?[...new Set(Object.values(attempts).filter(a=>
    a.viewId.startsWith('draft:')&&!isTerminal(a.phase)).map(a=>a.viewId))]:[];
  return <main className="history-shell product-shell" dir="rtl">
    <a href="#product-main" className="history-skip" inert={mobileOpen}>
      رفتن به محتوای اصلی گفت‌وگو
    </a>
    <aside ref={mobileMenu} id="product-chat-sidebar" className={'history-sidebar'+(mobileOpen?' is-mobile-open':'')}
      role={mobileOpen?'dialog':undefined} aria-modal={mobileOpen?'true':undefined}
      aria-label="فهرست گفتگوها">
      <button type="button" className="history-mobile-close" aria-label="بستن فهرست"
        onClick={()=>setMobileOpen(false)}>×</button>
      <div className="history-brand"><span className="brand-mark" aria-hidden="true">ف</span>
        <strong>راگ مالی</strong></div>
      <div className="history-actions">
        <button type="button" className="nav-new-chat" onClick={newConversation}
          data-testid="create-conversation" disabled={!verifiedPage||!canSend}>
          گفت‌وگوی تازه
        </button>
        <span className="history-note">گفت‌وگو با ثبت اولین پرسش در سرور ایجاد می‌شود.</span>
      </div>
      <p className="nav-section-title">گفت‌وگوهای حساب شما</p>
      {pendingDrafts.length>0&&<div className="history-list" aria-label="پرسش‌های در انتظار دریافت شناسهٔ گفتگو">
        {pendingDrafts.map(draft=><button type="button" key={draft}
          className={'nav-thread'+(selected===draft?' is-current':'')}
          onClick={()=>{setSelected(draft);setMobileOpen(false);}}>
          <span className="nav-thread-text">پرسش در انتظار ثبت سروری</span>
        </button>)}
      </div>}
      <p role="status" data-testid="history-state" className="history-state">
        {listState==='loading'?'در حال بارگذاری…':
        listState==='unauthorized'?'نشست پایان یافته است.':
        listState==='error'?'تاریخچه در دسترس نیست.':
        list.items.length===0?'هنوز گفت‌وگویی ثبت نشده است.':''}
      </p>
      <nav aria-label="مکالمات ثبت‌شده" className="history-list">
        {list.items.map(c=><button type="button" key={c.id}
          className={'nav-thread'+(selected===c.id?' is-current':'')}
          data-testid={'conversation-'+c.id}
          aria-current={selected===c.id?'page':undefined}
          onClick={()=>{setSelected(c.id);setMobileOpen(false);}}>
          <span className="nav-thread-text">{c.title??'گفت‌وگوی بدون عنوان'}</span>
          <span className="history-thread-detail">{c.id.slice(-8)}</span>
        </button>)}
      </nav>
      {list.more&&<button type="button" className="secondary"
        data-testid="more-conversations"
        onClick={()=>void loadList(true,list.next)}>نمایش گفت‌وگوهای بیشتر</button>}
      <button type="button" className="secondary" data-testid="refresh-history"
        onClick={()=>void loadList()} disabled={listState==='unauthorized'}>بازخوانی</button>
      <div className="history-sidebar-bottom">
        <Link href="/login" className="history-link">حساب کاربری و خروج امن</Link>
      </div>
    </aside>
    {mobileOpen&&<button type="button" className="history-mobile-scrim"
      aria-hidden="true" tabIndex={-1} onClick={()=>setMobileOpen(false)}/>}
    <section className="history-main" aria-labelledby="product-main" inert={mobileOpen}>
      <header className="history-mobile-topbar">
        <button className="mobile-menu-trigger" type="button"
          ref={menuTrigger} aria-label="بازکردن فهرست گفت‌وگوها" aria-controls="product-chat-sidebar"
          aria-expanded={mobileOpen} onClick={()=>setMobileOpen(true)}>☰</button>
        <span className="mobile-brand">راگ مالی</span>
        <Link href="/login" className="history-link">حساب و خروج</Link>
      </header>
      <header className="history-heading">
        <h1 id="product-main" tabIndex={-1}>گفت‌وگوی مالی</h1>
        <p>پرسش فارسی، تاریخچهٔ خصوصی و وضعیت واقعی هر Attempt؛ بدون پاسخ نمونه.</p>
        <p className="history-note" data-testid="educational-boundary">
          شواهد بازیابی فنی به‌تنهایی پاسخ یا توصیهٔ مالی تأییدشده نیستند.
          در این نسخه تولید پاسخ و پیوند استناد از مشاهدات بازیابی فعال نیست.
        </p>
        <p role="status" className="history-note" data-testid="app-runtime-capability">
          {capabilityState==='loading'
            ?'در حال بررسی قابلیت اجرای پرسش از سرور…'
            :capabilityState==='unavailable'
            ?'قابلیت ارسال از سرور قابل تأیید نیست؛ ارسال غیرفعال است.'
            :runtimeCapability.send_mode==='DISABLED'
            ?'برنامه در حالت بدون موتور فعال است؛ ارسال پرسش و تولید پاسخ غیرفعال است. تاریخچه فقط پس از ورود و اتصال امن به سرور داده قابل مشاهده است.'
            :'فقط ثبت و بازیابی فنی NO_DISPATCH_ONLY مجاز است؛ تولید پاسخ و موتور زنده فعال نیست.'}
        </p>
        <Link className="history-link" href="/account">حساب، حریم خصوصی و وضعیت قابلیت‌ها</Link>
      </header>
      {listState==='unauthorized'&&<p role="alert" data-testid="history-login-required">
        برای مشاهدهٔ گفت‌وگوها باید <Link href="/login">وارد حساب شوید</Link>.
      </p>}
      {error&&<p className="history-error" role="alert">{error}</p>}
      {listState==='error'&&<p role="status" data-testid="history-owner-revalidation-required"
        className="history-note">
        اتصال برای تأیید مالک و نشست برقرار نیست؛ پیام‌های قبلی موقتاً پنهان
        و ارسال پرسش تا بازخوانی موفق غیرفعال است.
      </p>}
      <div className="history-messages" aria-live="polite">
        {!messagesFor&&!selectedAttempts.length&&listState!=='unauthorized'&&
          <p className="history-empty">پرسشتان را بنویسید یا گفت‌وگویی از فهرست باز کنید.</p>}
        {(messagesFor?.items??[]).map(m=><article key={m.id}
          data-testid={'history-message-'+m.id}
          className={m.role==='user'?'history-user':'history-answer'}>
          {m.role==='user'
            ?<p className="history-message-text">{m.text}</p>
            :answers.has(m.id)
            ?<AnswerPanel answer={answers.get(m.id)!}/>
            :<p role="status" className="history-note">
              پاسخ فاقد شاهد معتبر است؛ محتوای آن نمایش داده نمی‌شود.
            </p>}
        </article>)}
        {selectedAttempts.map(a=><article key={a.record.client_message_id}
          className="history-answer product-attempt"
          data-testid={'attempt-'+a.record.client_message_id}>
          {a.question&&(!a.messageId||!renderedIds.has(a.messageId))&&
            <p className="history-message-text">{a.question}</p>}
          <p role="status" className="history-note">{phaseLabel(a)}</p>
          {a.attemptId&&<p className="history-note">شناسهٔ Attempt: <code>{a.attemptId}</code></p>}
          {a.engine&&<section className="history-note"
            data-testid={'engine-status-'+a.record.client_message_id}
            aria-label="وضعیت فنی همین درخواست">
            <p role="status">{engineLabel(a.engine)}</p>
            {a.engine.state==='CONTEXT_READY'&&<p>
              شواهد بازیابی‌شده: {a.engine.top10Count}، تعداد تولید پاسخ: {a.engine.generationCalls}
            </p>}
            <p>این گزارش فنی پاسخ مدل یا استناد قابل‌نمایش نیست.</p>
          </section>}
          {a.attemptId&&<RetrievedSourcesPanel
            receipt={a.sources} unavailable={a.sourcesUnavailable}/>}
          {a.engineUnavailable&&<p role="status" className="history-note">
            وضعیت فنی جداگانه در دسترس نیست؛ فقط وضعیت اصلی پیگیری می‌شود.
          </p>}
          {a.phase==='answer_committed'&&a.answer&&
            !renderedIds.has(a.answer.message_id)&&<AnswerPanel answer={a.answer}/>}
          {a.phase==='invalid_answer'&&<p className="history-note">
            محتوای دریافت‌شده از منبع آزمایشی قابل ارائه نیست.
          </p>}
          {!isTerminal(a.phase)&&<button type="button" className="secondary"
            data-testid="recover-status" onClick={()=>void probe(a.record)}>
            بررسی وضعیت همین Attempt
          </button>}
        </article>)}
        {messagesFor?.more&&<button type="button" className="secondary"
          data-testid="more-messages"
          onClick={()=>void loadThread(selected,true,messagesFor.next)}>
          پیام‌های بیشتر
        </button>}
      </div>
      {listState!=='unauthorized'&&<form className="history-compose" onSubmit={e=>void submit(e)}>
        <label htmlFor="product-question" className="sr-only">پرسش فارسی</label>
        <div className="composer">
          <textarea id="product-question" rows={2} data-testid="history-question"
            value={drafts[selected]??''} disabled={busy||!verifiedPage||!canSend}
            onChange={e=>setDrafts(all=>({...all,[selected]:e.target.value}))}
            placeholder="سؤال خود را به فارسی بنویسید…"/>
          <button type="submit" className="primary" data-testid="history-send"
            disabled={busy||!verifiedPage||!canSend||!(drafts[selected]??'').trim()}>ارسال پرسش</button>
        </div>
        <p className="under-composer">
          با Refresh یا قطع ارتباط، درخواست تکرار نمی‌شود؛ فقط وضعیت آن از سرور خوانده می‌شود.
        </p>
      </form>}
    </section>
  </main>;
}
