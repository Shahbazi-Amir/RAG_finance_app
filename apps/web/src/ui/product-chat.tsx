'use client';
import {useCallback,useEffect,useRef,useState,type FormEvent} from 'react';
import Link from 'next/link';
import {conversations,messages,newSend,sendMessage,recoverStatus,recoverEngineStatus,recoverRetrievedSources,HistoryFailure,
  failureLabel,mergeUnique,type ConversationView,type MessageView,
  type AnswerView,type HistoryStatus,type EngineStatus,type RetrievedSources} from '../history/client';
import type {Answer,Citation} from '../mock/transport';
import {verifiedSourceUrl} from './source-locator';
import {isVerifiedLiveAnswer,productOutcomeLabel} from './answer-visibility';
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
  return <li className="product-citation">
    <span>شناسهٔ منبع: <code dir="ltr">{s.source_id??'ثبت نشده'}</code></span>
    {s.display_title&&s.display_title_origin!=='SYNTHETIC'&&
      <span>عنوان: {s.display_title}</span>}
    <span>شناسهٔ استناد: <code dir="ltr">{citation.citation_id}</code></span>
    <span>نقل‌قول مستقیم منبع: در این قرارداد ارائه نشده است.</span>
    {s.locator?.kind==='book_page'&&s.locator.page!==null&&
      <span>صفحهٔ ثبت‌شده: {s.locator.page}</span>}
    {s.locator?.kind==='transcript_timestamp'&&s.locator.timestamp_ms!==null&&
      <span>زمان ثبت‌شده (میلی‌ثانیه): {s.locator.timestamp_ms}</span>}
    {href?<a href={href} target="_blank" rel="noopener noreferrer">بازکردن پیوند معتبر منبع</a>
      :<span className="history-note">Locator این شاهد پیوند وب معتبر ندارد.</span>}
  </li>;
}
function AnswerPanel({answer}:{answer:Answer}){
  if(!isVerifiedLiveAnswer(answer))return <p role="status" className="history-note">
    پاسخ نمونه یا تأییدنشده از API دریافت شده و عمداً نمایش داده نمی‌شود.
  </p>;
  return <div className="product-answer" data-testid={'answer-'+answer.answer_id}>
    {answer.answer_text&&<p className="history-message-text">{answer.answer_text}</p>}
    {productOutcomeLabel(answer)&&<p role="status" className="history-note">{productOutcomeLabel(answer)}</p>}
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
  const [busy,setBusy]=useState(false);
  const lost=useRef(false);
  const sending=useRef(false);
  const polling=useRef(new Set<string>());
  const attemptsRef=useRef(attempts);
  const threadEpochs=useRef<Record<string,number>>({});
  useEffect(()=>{attemptsRef.current=attempts},[attempts]);
  const invalidate=useCallback((e:unknown):boolean=>{
    if(!(e instanceof HistoryFailure&&e.reason==='unauthorized'))return false;
    lost.current=true;
    const s=sessionStore();if(s)forgetCheckpoints(s);
    attemptsRef.current={};
    threadEpochs.current={};
    setAttempts({});setList({items:[],next:null,more:false});
    setThreads({});setSelected('draft:new');setDrafts({});
    setListState('unauthorized');setError('');
    return true;
  },[]);
  const loadList=useCallback(async (append=false,cursor:string|null=null)=>{
    if(lost.current)return;
    try{
      // Keep the existing #49 browser A/B harness query `limit=2` stable.
      const page=await conversations(2,append?cursor:null);
      if(lost.current)return;
      setList(prev=>({items:append?mergeUnique(prev.items,page.items,x=>x.id):page.items,
        next:page.next,more:page.more}));
      setListState('ready');
      if(!append)setSelected(current=>current==='draft:new'&&page.items.length?
        page.items[0].id:current);
    }catch(e){if(!invalidate(e)&&!lost.current){setListState('error');setError(failureLabel(e));}}
  },[invalidate]);
  const loadThread=useCallback(async (id:string,append=false,cursor:string|null=null)=>{
    if(lost.current||id.startsWith('draft:'))return;
    const epoch=(threadEpochs.current[id]??0)+1;
    threadEpochs.current[id]=epoch;
    try{
      const page=await messages(id,30,append?cursor:null);
      if(lost.current||threadEpochs.current[id]!==epoch)return;
      setThreads(all=>{
        const prev=all[id];
        return {...all,[id]:{
          items:append&&prev?mergeUnique(prev.items,page.items,x=>x.id):page.items,
          answers:append&&prev?mergeUnique(prev.answers,page.answers,x=>x.id):page.answers,
          next:page.next,more:page.more
        }};
      });
    }catch(e){if(!invalidate(e)&&!lost.current)setError(failureLabel(e));}
  },[invalidate]);
  const probe=useCallback(async (record:AttemptCheckpoint)=>{
    if(lost.current||polling.current.has(record.client_message_id))return;
    polling.current.add(record.client_message_id);
    try{
      const status=await recoverStatus(statusCorrelators(record));
      if(lost.current)return;
      const old=attemptsRef.current[record.client_message_id];
      if(old?.attemptId&&status.attemptId&&old.attemptId!==status.attemptId){
        setAttempts(all=>({...all,[record.client_message_id]:{
          ...all[record.client_message_id],phase:'status_error'}}));
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
          if(invalidate(e)||lost.current)return;
          sourcesUnavailable=true;
        }
      }
      if(lost.current)return;
      setAttempts(all=>{
        const previous=all[record.client_message_id];
        if(!previous||isTerminal(previous.phase))return all;
        return {...all,[record.client_message_id]:{
          ...previous,phase:resultPhase,attemptId:status.attemptId??previous.attemptId,
          messageId:status.messageId,answer:status.answer,
          engine:technical??previous.engine,engineUnavailable,
          sources:sources??previous.sources,sourcesUnavailable,
          record:status.id?{...previous.record,resolved_conversation_id:status.id}:previous.record,
          viewId:status.id??previous.viewId,
          confirmed:status.status!=='not_found'
        }};
      });
      const confirmedId=status.id;
      if(confirmedId&&status.status!=='not_found'){
        const s=sessionStore();if(s)retainCheckpoint(s,{...record,resolved_conversation_id:confirmedId});
        setSelected(old=>old.startsWith('draft:')?confirmedId:old);
        void loadList();
        void loadThread(confirmedId);
      }
    }catch(e){
      if(!invalidate(e)&&!lost.current)
        setAttempts(all=>{
          const prev=all[record.client_message_id];
          return prev&&!isTerminal(prev.phase)?{...all,[record.client_message_id]:
            {...prev,phase:'status_error'}}:all;
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
      void loadList();
      for(const record of saved)void probe(record);
    });
    return ()=>{active=false;};
  },[loadList,probe]);
  useEffect(()=>{
    if(!selected||selected.startsWith('draft:'))return;
    let active=true;
    // Fetch in a scheduled callback, not synchronously in an Effect.
    // Cancel the callback when a newer conversation is selected.
    queueMicrotask(()=>{
      if(active)void loadThread(selected);
    });
    return ()=>{active=false;};
  },[selected,loadThread]);
  useEffect(()=>{
    const timer=window.setInterval(()=>{
      if(lost.current||document.visibilityState==='hidden')return;
      for(const attempt of Object.values(attemptsRef.current)){
        if(!isTerminal(attempt.phase))void probe(attempt.record);
      }
    },4500);
    return ()=>window.clearInterval(timer);
  },[probe]);
  function newConversation(){
    if(lost.current)return;
    const id='draft:'+crypto.randomUUID();
    setSelected(id);setDrafts(all=>({...all,[id]:''}));setMobileOpen(false);
  }
  async function submit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();
    if(lost.current||sending.current)return;
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
  const messagesFor=threads[selected];
  const renderedIds=new Set(messagesFor?.items.map(m=>m.id)??[]);
  const answers=new Map((messagesFor?.answers??[]).map(a=>[a.messageId,a.payload]));
  const selectedAttempts=Object.values(attempts).filter(a=>a.viewId===selected);
  const pendingDrafts=[...new Set(Object.values(attempts).filter(a=>
    a.viewId.startsWith('draft:')&&!isTerminal(a.phase)).map(a=>a.viewId))];
  return <main className="history-shell product-shell" dir="rtl">
    <aside className={'history-sidebar'+(mobileOpen?' is-mobile-open':'')}
      role={mobileOpen?'dialog':undefined} aria-modal={mobileOpen?'true':undefined}
      aria-label="فهرست گفتگوها">
      <button type="button" className="history-mobile-close" aria-label="بستن فهرست"
        onClick={()=>setMobileOpen(false)}>×</button>
      <div className="history-brand"><span className="brand-mark" aria-hidden="true">ف</span>
        <strong>راگ مالی</strong></div>
      <div className="history-actions">
        <button type="button" className="nav-new-chat" onClick={newConversation}
          data-testid="create-conversation" disabled={listState==='unauthorized'}>
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
        onClick={()=>void loadList(true,list.next)}>نمایش گفت‌وگوهای بیشتر</button>}
      <button type="button" className="secondary" data-testid="refresh-history"
        onClick={()=>void loadList()} disabled={listState==='unauthorized'}>بازخوانی</button>
      <div className="history-sidebar-bottom">
        <Link href="/login" className="history-link">حساب کاربری و خروج امن</Link>
      </div>
    </aside>
    <section className="history-main" aria-label="گفت‌وگوی فارسی">
      <header className="history-mobile-topbar">
        <button className="mobile-menu-trigger" type="button"
          aria-label="بازکردن فهرست گفت‌وگوها" onClick={()=>setMobileOpen(true)}>☰</button>
        <span className="mobile-brand">راگ مالی</span>
        <Link href="/login" className="history-link">حساب و خروج</Link>
      </header>
      {mobileOpen&&<button type="button" className="history-mobile-scrim"
        aria-label="بستن فهرست" onClick={()=>setMobileOpen(false)}/>}
      <header className="history-heading">
        <h1>گفت‌وگوی مالی</h1>
        <p>پرسش فارسی، تاریخچهٔ خصوصی و وضعیت واقعی هر Attempt؛ بدون پاسخ نمونه.</p>
      </header>
      {listState==='unauthorized'&&<p role="alert" data-testid="history-login-required">
        برای مشاهدهٔ گفت‌وگوها باید <Link href="/login">وارد حساب شوید</Link>.
      </p>}
      {error&&<p className="history-error" role="alert">{error}</p>}
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
          {a.sources?.retrievalState==='PARTIAL_UNVERIFIED'&&a.sources.rows.length>0&&
            <section aria-label="قطعه‌های بازیابی‌شدهٔ همین Attempt"
              data-testid={'retrieved-sources-'+a.record.client_message_id}
              className="product-evidence">
              <h2>قطعه‌های بازیابی‌شده (اعتبار استناد تأیید نشده)</h2>
              <ol>{a.sources.rows.map(row=><li key={row.position}>
                <span>رتبهٔ بازیابی: {row.position} </span>
                <span>شناسهٔ قطعه: <code dir="ltr">{row.chunkId}</code></span>
                <span> شناسهٔ مشاهده‌شدهٔ منبع: <code dir="ltr">{row.sourceId??'ثبت نشده'}</code></span>
              </li>)}</ol>
              <p className="history-note">هیچ لینک یا انتساب تأییدشده‌ای موجود نیست؛
                این فهرست پاسخ تولیدشده یا استناد معتبر نیست.</p>
            </section>}
          {a.sourcesUnavailable&&<p role="status" className="history-note">
            رسید مستقل منابع قابل بازیابی نیست؛ وضعیت فنی بدون تغییر باقی می‌ماند.
          </p>}
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
          onClick={()=>void loadThread(selected,true,messagesFor.next)}>
          پیام‌های بیشتر
        </button>}
      </div>
      {listState!=='unauthorized'&&<form className="history-compose" onSubmit={e=>void submit(e)}>
        <label htmlFor="product-question" className="sr-only">پرسش فارسی</label>
        <div className="composer">
          <textarea id="product-question" rows={2} data-testid="history-question"
            value={drafts[selected]??''} disabled={busy}
            onChange={e=>setDrafts(all=>({...all,[selected]:e.target.value}))}
            placeholder="سؤال خود را به فارسی بنویسید…"/>
          <button type="submit" className="primary" data-testid="history-send"
            disabled={busy||!(drafts[selected]??'').trim()}>ارسال پرسش</button>
        </div>
        <p className="under-composer">
          با Refresh یا قطع ارتباط، درخواست تکرار نمی‌شود؛ فقط وضعیت آن از سرور خوانده می‌شود.
        </p>
      </form>}
    </section>
  </main>;
}
