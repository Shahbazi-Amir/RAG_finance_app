'use client';
import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import {
  CONTRACT_VERSION,FIXTURE_ORIGIN,MockTransport,SCENARIOS,isRealSourceClaim,
  newRequest,safeSourceHref,terminalDisplay,
  type Answer,type Scenario,type SendReceipt,type SendRequest,type Source
} from '../src/mock/transport';

type Item={key:string;request:SendRequest;scenario:Scenario;receipt?:SendReceipt;
  text:string;answer?:Answer;phase:string;terminal?:string;isRunning:boolean;
  cancelRequested:boolean;displayStopped?:boolean;warning?:string};
const scenarioNames:Record<Scenario,string>={
  answer:'پاسخ نمونه با منبع',partial:'پاسخ ناقص',no_answer:'بدون پاسخ',
  clarification:'نیازمند توضیح',refusal:'امتناع',error:'خطای فنی',
  unknown:'وضعیت نامعلوم',malicious:'آزمایش محتوای مخرب (امن)'
};
const phaseNames:Record<string,string>={
  submitting:'در حال ارسال پرسش',connected:'در حال آماده‌سازی پاسخ نمونه',
  retrieving:'مرحلهٔ جست‌وجوی شبیه‌سازی‌شده',generating:'مرحلهٔ تولید شبیه‌سازی‌شده',
  delta:'در حال نمایش پاسخ',completed:'نمایش پاسخ پایان یافت',
  'display-stopped':'نمایش پاسخ متوقف شد؛ پردازش متوقف‌شده تأیید نشده است',
  'cancel-requested':'درخواست توقف پردازش ارسال شد؛ هنوز تأیید نشده است',
  'server-cancelled':'توقف پردازش در شبیه‌ساز تأیید شد',failed:'خطا در پردازش نمونه',
  unknown:'نتیجهٔ پردازش مشخص نیست',conflict:'درخواست تکراری پذیرفته نشد',
  replayed:'درخواست قبلی دوباره دریافت شد'
};

type ItemStatus={label:string;tone:'pending'|'caution'|'error'};
function visibleStatus(item:Item):ItemStatus|null{
  // A completed normal answer has no redundant status. Terminal outcomes stay distinct.
  if(item.terminal==='conflict')
    return {label:'درخواست تکراری با متن متفاوت پذیرفته نشد؛ پیام جدیدی ثبت نشد.',tone:'error'};
  if(item.displayStopped||item.terminal==='display-only')
    return {label:'نمایش پاسخ متوقف شد؛ توقف پردازش تأیید نشده است.',tone:'caution'};
  if(item.terminal==='server-cancelled')
    return {label:'توقف پردازش در شبیه‌ساز تأیید شد.',tone:'caution'};
  if(item.terminal==='failed')
    return {label:'خطای فنی رخ داد؛ پاسخ کامل دریافت نشد.',tone:'error'};
  if(item.terminal==='unknown')
    return {label:'نتیجه مشخص نیست؛ پاسخ کامل تأیید نشده است.',tone:'caution'};
  if(item.terminal==='partial'||item.answer?.outcome==='partial')
    return {label:'پاسخ ناقص است؛ نتیجهٔ کامل دریافت نشده است.',tone:'caution'};
  if(item.answer){
    if(item.answer.outcome==='no_answer')
      return {label:'شواهد کافی برای پاسخ در این نمونه وجود ندارد.',tone:'caution'};
    if(item.answer.outcome==='clarification')
      return {label:'برای پاسخ دقیق‌تر، پرسش را روشن‌تر کنید.',tone:'caution'};
    if(item.answer.outcome==='refusal')
      return {label:'در این نمونه امکان پاسخ‌گویی وجود ندارد.',tone:'caution'};
    if(item.answer.outcome==='answer')return null;
    return {label:'وضعیت پاسخ نمونه مشخص نیست.',tone:'caution'};
  }
  if(item.terminal==='complete'||item.phase==='completed')return null;
  return {label:phaseNames[item.phase]??'در حال آماده‌سازی پاسخ نمونه',tone:'pending'};
}

function SourceDrawer({source,claim,onClose}:{source:Source;claim:string;onClose:()=>void}){
  const closeRef=useRef<HTMLButtonElement>(null);
  const panelRef=useRef<HTMLElement>(null);
  useEffect(()=>{closeRef.current?.focus()},[]);
  function handleDialogKeyDown(event:ReactKeyboardEvent<HTMLElement>){
    if(event.key==='Escape'){
      event.preventDefault();event.stopPropagation();onClose();return;
    }
    if(event.key!=='Tab')return;
    const panel=panelRef.current;
    if(!panel)return;
    const focusable=Array.from(panel.querySelectorAll<HTMLElement>(
      'button:not([disabled]), a[href]:not([aria-disabled="true"]), [tabindex]:not([tabindex="-1"])'
    )).filter(element=>element.getClientRects().length>0);
    if(focusable.length===0){event.preventDefault();panel.focus();return;}
    const first=focusable[0],last=focusable[focusable.length-1];
    if(event.shiftKey&&(document.activeElement===first||!panel.contains(document.activeElement))){
      event.preventDefault();last.focus();
    }else if(!event.shiftKey&&(document.activeElement===last||!panel.contains(document.activeElement))){
      event.preventDefault();first.focus();
    }
  }
  const href=safeSourceHref(source);
  return <div className="drawer-backdrop" onClick={onClose}>
    <aside ref={panelRef} tabIndex={-1} className="drawer" role="dialog" aria-modal="true" aria-label="جزئیات منبع نمونه"
      onKeyDown={handleDialogKeyDown} onClick={event=>event.stopPropagation()}>
      <div className="drawer-head"><h2>جزئیات منبع</h2>
        <button ref={closeRef} className="icon-button" onClick={onClose} aria-label="بستن پنل منبع">×</button>
      </div>
      <p className="hint">اطلاعات این منبع نمونه‌اند؛ محل شاهد و انتساب واقعی آن تأیید نشده‌اند.</p>
      <p className="eyebrow">ادعای مرتبط</p><p className="plain-value">{claim}</p>
      <dl className="source-meta">
        <dt>عنوان دریافت‌شده</dt>
        <dd>{source.display_title&&source.display_title_origin?source.display_title:'عنوانی ارائه نشده'}</dd>
        <dt>منشأ اعلام‌شدهٔ عنوان</dt><dd>{source.display_title_origin==='SYNTHETIC'?'دادهٔ ساختگی آزمایشی':source.display_title_origin==='source_record'?'اطلاعات منبع':source.display_title_origin==='catalog_record'?'فهرست منابع':'نامشخص'}؛ اصالت آن تأیید نشده است</dd>
        <dt>نوع منبع</dt><dd>{source.source_type==='book'?'کتاب':source.source_type==='transcript'?'متن گفتار':source.source_type?'نوع ثبت‌شدهٔ دیگر':'نامشخص'}</dd>
        <dt>محل شاهد</dt><dd>{source.resolution_status==='verified'?'از قرارداد حل‌شده گزارش شده':'حل‌نشده'}</dd>
        <dt>انتساب</dt><dd>{source.attribution_status==='verified'?'از قرارداد تأییدشده گزارش شده':'تأییدنشده'}</dd>
        <dt>نویسنده</dt><dd>{source.credited_author_name??'ارائه نشده'}</dd>
        <dt>ناظر/سردبیر</dt><dd>{source.editorial_supervisor_name??'ارائه نشده'}</dd>
        <dt>گوینده</dt><dd>{source.speaker_name??'ارائه نشده'}</dd>
      </dl>
      {isRealSourceClaim(source)&&href
        ?<a href={href} target="_blank" rel="noopener noreferrer" className="primary link">بازکردن منبع مجاز</a>
        :<p className="disabled-link" role="status">بازکردن منبع غیرفعال است؛ مقصد/مجوز اثبات نشده است.</p>}
      <button className="secondary wide" onClick={onClose}>بازگشت به گفتگو</button>
    </aside>
  </div>
}

type ProductView='chat'|'account'|'privacy';
type NavProps={
  view:ProductView;collapsed:boolean;mobile?:boolean;
  hasConversation:boolean;conversationPreview:string;
  onView:(view:ProductView)=>void;onNewChat:()=>void;onToggle?:()=>void;
};
function Navigation({view,collapsed,mobile=false,hasConversation,conversationPreview,onView,onNewChat,onToggle}:NavProps){
  return <div className={"nav-content"+(collapsed?" nav-compact":"")}>
    <div className="nav-brand-row">
      <div className="nav-brand">
        <span className="brand-mark" aria-hidden="true">ف</span>
        <span className="nav-label nav-brand-name">راگ مالی</span>
      </div>
      {!mobile&&<button type="button" className="nav-collapse" onClick={onToggle}
        aria-label={collapsed?'بازکردن نوار کناری':'جمع‌کردن نوار کناری'}
        aria-expanded={!collapsed} title={collapsed?'بازکردن نوار کناری':'جمع‌کردن نوار کناری'}>
        <span aria-hidden="true">{collapsed?'‹':'›'}</span>
      </button>}
    </div>
    <button type="button" className="nav-new-chat" onClick={onNewChat}
      title="گفتگوی تازه؛ گفتگوی فعلی از حافظهٔ همین صفحه پاک می‌شود"
      aria-label="گفتگوی تازه؛ پاک‌کردن گفتگوی موقت همین صفحه">
      <span className="nav-icon" aria-hidden="true">＋</span>
      <span className="nav-label">گفتگوی تازه</span>
    </button>
    <p className="nav-helper nav-label">گفتگوی تازه، پیام‌های موقت همین صفحه را پاک می‌کند.</p>
    <nav className="nav-main-links" aria-label="صفحه‌های محصول">
      <button type="button" className={"nav-link"+(view==='chat'?' is-current':'')}
        aria-current={view==='chat'?'page':undefined} aria-label="صفحهٔ گفتگو"
        title="صفحهٔ گفتگو" onClick={()=>onView('chat')}>
        <span className="nav-icon" aria-hidden="true">▤</span>
        <span className="nav-label">گفتگو</span>
      </button>
    </nav>
    <section className="nav-temporary" aria-label="گفتگوهای موقت این صفحه">
      <p className="nav-section-title nav-label">گفتگوهای این صفحه</p>
      {hasConversation?
        <button type="button" className="nav-thread" onClick={()=>onView('chat')}
          aria-label={"بازگشت به گفتگوی موقت: "+conversationPreview}
          title={"گفتگوی موقت: "+conversationPreview}>
          <span className="nav-icon" aria-hidden="true">◉</span>
          <span className="nav-label nav-thread-text">{conversationPreview}</span>
        </button>
        :<p className="nav-empty nav-label">هنوز گفتگویی در این صفحه ندارید.</p>}
      <p className="nav-local-notice nav-label">فهرست تاریخی یا ذخیره‌سازی دائمی فعال نیست.</p>
    </section>
    <nav className="nav-bottom" aria-label="حساب و حریم خصوصی">
      <button type="button" className={"nav-link"+(view==='account'?' is-current':'')}
        aria-current={view==='account'?'page':undefined} aria-label="حساب کاربری"
        title="حساب کاربری" onClick={()=>onView('account')}>
        <span className="nav-icon" aria-hidden="true">◯</span>
        <span className="nav-label">حساب کاربری</span>
      </button>
      <button type="button" className={"nav-link"+(view==='privacy'?' is-current':'')}
        aria-current={view==='privacy'?'page':undefined} aria-label="حریم خصوصی"
        title="حریم خصوصی" onClick={()=>onView('privacy')}>
        <span className="nav-icon" aria-hidden="true">◇</span>
        <span className="nav-label">حریم خصوصی</span>
      </button>
    </nav>
  </div>;
}

export default function HomePage(){
  // The mock transport has no render-time side effects; initialize lazily once per chat.
  // Keep the mock instance in state so render never reads or writes a mutable ref.
  const [transport,setTransport]=useState<MockTransport>(()=>new MockTransport());
  const [view,setView]=useState<ProductView>('chat');
  const [sidebarCollapsed,setSidebarCollapsed]=useState(false);
  const [mobileMenuOpen,setMobileMenuOpen]=useState(false);
  const mobileTriggerRef=useRef<HTMLButtonElement>(null);
  const mobileCloseRef=useRef<HTMLButtonElement>(null);
  const mobileDialogRef=useRef<HTMLDivElement>(null);
  const [draft,setDraft]=useState('تفاوت پس‌انداز و سرمایه‌گذاری چیست؟');
  const [scenario,setScenario]=useState<Scenario>('answer');
  const [items,setItems]=useState<Item[]>([]);
  const [threadId,setThreadId]=useState<string|null>(null);
  const [activeKey,setActiveKey]=useState<string|null>(null);
  useEffect(()=>{
    if(!mobileMenuOpen)return;
    const previousOverflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    mobileCloseRef.current?.focus();
    return ()=>{document.body.style.overflow=previousOverflow};
  },[mobileMenuOpen]);
  function closeMobileMenu(){
    setMobileMenuOpen(false);
    window.requestAnimationFrame(()=>mobileTriggerRef.current?.focus());
  }
  function onMobileKeyDown(event:ReactKeyboardEvent<HTMLDivElement>){
    if(event.key==='Escape'){
      event.preventDefault();event.stopPropagation();closeMobileMenu();return;
    }
    if(event.key!=='Tab')return;
    const dialog=mobileDialogRef.current;
    if(!dialog)return;
    const focusable=Array.from(dialog.querySelectorAll<HTMLElement>(
      'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
    )).filter(element=>element.getClientRects().length>0);
    if(!focusable.length){event.preventDefault();dialog.focus();return}
    const first=focusable[0],last=focusable[focusable.length-1];
    if(event.shiftKey&&(document.activeElement===first||!dialog.contains(document.activeElement))){
      event.preventDefault();last.focus();
    }else if(!event.shiftKey&&(document.activeElement===last||!dialog.contains(document.activeElement))){
      event.preventDefault();first.focus();
    }
  }
  function navigate(next:ProductView){
    setView(next);
    if(mobileMenuOpen)closeMobileMenu();
  }

  const [drawer,setDrawer]=useState<{source:Source;claim:string}|null>(null);
  const drawerOpener=useRef<HTMLButtonElement|null>(null);
  function closeSource(){
    setDrawer(null);
    // Return focus after the modal has left the DOM.
    window.requestAnimationFrame(()=>drawerOpener.current?.focus());
  }
  const suppress=useRef(new Set<string>());
  const token=useRef(0);
  const endRef=useRef<HTMLDivElement>(null);
  useEffect(()=>{if(items.length>0)endRef.current?.scrollIntoView({block:'end',behavior:'smooth'})},[items.length]);
  function patch(key:string,part:Partial<Item>){
    setItems(old=>old.map(i=>i.key===key?{...i,...part}:i));
  }
  async function run(req:SendRequest,chosen:Scenario){
    const key=req.client_message_id,runId=++token.current;
    suppress.current.delete(key);
    setActiveKey(key);
    setItems(old=>old.some(i=>i.key===key)
      ?old.map(i=>i.key===key?{...i,request:req,scenario:chosen,receipt:undefined,
        phase:'submitting',isRunning:true,cancelRequested:false,terminal:undefined,
        text:'',answer:undefined,warning:undefined,displayStopped:false}:i)
      :[...old,{key,request:req,scenario:chosen,phase:'submitting',text:'',
        isRunning:true,cancelRequested:false}]);
    let cumulative='';
    try{
      for await(const u of transport.send(req,chosen)){
        if(runId!==token.current||suppress.current.has(key))return;
        if(u.kind==='receipt'){
          if(u.receipt.disposition==='conflict'){
            patch(key,{receipt:u.receipt,phase:'conflict',terminal:'conflict',isRunning:false});
            return;
          }
          if(u.receipt.resolved_conversation_id&&!threadId)setThreadId(u.receipt.resolved_conversation_id);
          patch(key,{receipt:u.receipt,phase:u.receipt.disposition==='replayed'?'replayed':'connected'});
        }else if(u.kind==='event'){
          const e=u.event,result=terminalDisplay(e);
          if(e.event_type==='delta'&&typeof e.data.text==='string'){
            cumulative+=e.data.text; // exact; do not trim or normalize
            patch(key,{text:cumulative,phase:'delta'});
          }else if(result){
            patch(key,{phase:result==='complete'?'completed':result,terminal:result,isRunning:false,
              warning:result==='failed'?'خطای فنی نمونه؛ جزئیات داخلی پنهان است.':undefined});
          }else if((e.event_type==='retrieving'||e.event_type==='generating')&&e.data.reported_by==='backend'){
            patch(key,{phase:e.event_type});
          }else if(e.event_type==='cancel_requested'){
            patch(key,{phase:'cancel-requested',cancelRequested:true});
          }else if(e.event_type==='connected'){
            patch(key,{phase:'connected'});
          }
        }else{
          patch(key,{answer:u.answer,phase:'completed',
            terminal:u.answer.state==='partial'?'partial':'complete',isRunning:false});
        }
      }
    }catch{
      patch(key,{phase:'unknown',terminal:'unknown',isRunning:false,
        warning:'ارتباط آزمایشی نامعلوم است؛ نتیجه تأیید نشده.'});
    }finally{
      if(runId===token.current)setActiveKey(null);
    }
  }
  function submit(){
    if(!draft.trim()||activeKey)return;
    const suffix='ui_'+crypto.randomUUID().replaceAll('-','').slice(0,18);
    const req=newRequest(draft,threadId,suffix);
    void run(req,scenario);setDraft('');
  }
  const active=items.find(i=>i.key===activeKey);
  function cancelDisplay(){
    if(!activeKey)return;
    suppress.current.add(activeKey);
    patch(activeKey,{phase:'display-stopped',terminal:'display-only',
      isRunning:false,displayStopped:true});
    setActiveKey(null);
  }
  function cancelServer(){
    if(!active?.receipt||!active.isRunning||active.cancelRequested)return;
    transport.requestServerCancellation(active.receipt.request_id);
    // This flag is local UI state: a request is NOT proof of server cancellation.
    patch(active.key,{phase:'cancel-requested',cancelRequested:true});
  }
  function retryLatest(conflict=false){
    if(activeKey||!items.length)return;
    const latest=items[items.length-1];
    const req=conflict?{...latest.request,question:latest.request.question+' (متن تغییرکردهٔ آزمون تعارض)'}
      :latest.request;
    void run(req,latest.scenario);
  }
  function clearChat(){
    token.current++;setItems([]);setActiveKey(null);setThreadId(null);
    suppress.current.clear();setDrawer(null);setDraft('');
    setTransport(()=>new MockTransport());
  }
  function beginNewChat(){
    // Clearing is real but page-local; ask before losing a nonempty in-memory thread.
    if(items.length>0&&!window.confirm('گفتگوی آزمایشی فعلی از حافظهٔ این صفحه پاک شود؟ این کار قابل بازگشت نیست.')){
      return;
    }
    clearChat();setView('chat');
    if(mobileMenuOpen)closeMobileMenu();
  }
  const conversationPreview=items[0]?.request.question??'';
  const hasConversation=items.length>0;
  return <main className="app-shell" dir="rtl">
    <aside className={"sidebar-desktop"+(sidebarCollapsed?" is-collapsed":"")}
      aria-label="ناوبری اصلی">
      <Navigation view={view} collapsed={sidebarCollapsed} hasConversation={hasConversation}
        conversationPreview={conversationPreview} onView={navigate} onNewChat={beginNewChat}
        onToggle={()=>setSidebarCollapsed(value=>!value)}/>
    </aside>
    <div className="app-main">
      <header className="mobile-topbar">
        <button type="button" ref={mobileTriggerRef} aria-label="بازکردن منوی ناوبری"
          aria-haspopup="dialog" aria-controls="mobile-navigation" aria-expanded={mobileMenuOpen}
          onClick={()=>setMobileMenuOpen(true)} className="mobile-menu-trigger">
          <span aria-hidden="true">☰</span>
        </button>
        <span className="mobile-brand">راگ مالی</span>
      </header>
      <div className="workspace">
        {view==='chat'?<section className="chat-panel" aria-label="گفتگوی فارسی">
        <p className="demo-note" role="note">
          نسخهٔ آزمایشی؛ پاسخ‌ها نمونه‌اند و به موتور پاسخ‌گویی متصل نیستند.
        </p>
        <div className="messages" aria-live="polite" aria-relevant="additions text">
          {items.length===0&&<div className="empty-state">
            <div className="empty-icon" aria-hidden="true">✦</div>
            <h1>چه پرسشی دربارهٔ امور مالی دارید؟</h1>
            <p>برای دیدن یک پاسخ آزمایشی، سؤال خود را در کادر پایین بنویسید.</p>
            <p className="empty-example">مثلاً: چرا بودجه‌بندی ماهانه مهم است؟</p>
          </div>}
          {items.map(item=>{
            const status=visibleStatus(item);
            return <article className="message-set" key={item.key}>
              <div className="user-bubble">
                <p>{item.request.question}</p>
              </div>
              <div className="answer-bubble">
                <div className="answer-head">
                  <span className="assistant-icon" aria-hidden="true">ف</span>
                  <span className="message-label">پاسخ نمونه</span>
                </div>
                {status&&<p className="state-line" data-tone={status.tone} role="status">{status.label}</p>}
                {item.text&&<p className="answer-text">{item.text}</p>}
                {item.answer&&<>
                  {item.answer.claims.map(claim=><div className="claim" key={claim.claim_id}>
                    <p>{claim.text}</p>
                    {claim.citation_ids.map(cid=>{
                      const citation=item.answer!.citations.find(x=>x.citation_id===cid);
                      return citation?<button className="source-button" type="button" key={cid}
                        onClick={event=>{drawerOpener.current=event.currentTarget;setDrawer({source:citation.source,claim:claim.text});}}>
                        جزئیات منبع <span aria-hidden="true">↗</span>
                      </button>:null;
                    })}
                  </div>)}
                  {item.answer.confidence===null&&
                    <p className="confidence">اطمینان پاسخ ارزیابی نشده است.</p>}
                </>}
              </div>
            </article>;
          })}
          <div ref={endRef}/>
        </div>
        <div className="chat-footer">
          {active&&<div className="run-controls" role="group" aria-label="کنترل دریافت پاسخ">
            <div className="run-buttons">
              <button className="secondary" onClick={cancelDisplay} type="button">توقف نمایش</button>
              <button className="secondary" disabled={!active.receipt||!active.isRunning||active.cancelRequested}
                onClick={cancelServer} type="button">درخواست توقف پردازش</button>
            </div>
            <p className="run-note">توقف نمایش با توقف تأییدشدهٔ پردازش یکسان نیست.</p>
          </div>}
          <details className="test-tools">
            <summary>ابزارهای آزمایش <span aria-hidden="true">⌄</span></summary>
            <div className="tools-content">
              <div className="compose-tools">
                <label htmlFor="scenario">نوع پاسخ نمونه</label>
                <select id="scenario" value={scenario}
                  onChange={event=>setScenario(event.target.value as Scenario)} disabled={!!activeKey}>
                  {SCENARIOS.map(key=><option key={key} value={key}>{scenarioNames[key]}</option>)}
                </select>
              </div>
              {!activeKey&&items.length>0&&<div className="tool-actions">
                <button className="secondary" type="button" onClick={()=>retryLatest()}>تکرار همان درخواست (Replay)</button>
                <button className="secondary" type="button" onClick={()=>retryLatest(true)}>آزمایش تعارض (Conflict)</button>
              </div>}
              <p className="tools-description">این گزینه‌ها فقط رفتار رابط و داده‌های ساختگی را بررسی می‌کنند.</p>
              <div className="technical-meta">
                <span>نسخهٔ قرارداد: <code dir="ltr">{CONTRACT_VERSION}</code></span>
                <span>منشأ داده‌ها: <code dir="ltr">{FIXTURE_ORIGIN}</code></span>
              </div>
              {items.some(item=>item.receipt)&&<div className="receipt-list" aria-label="اطلاعات فنی درخواست‌ها">
                {items.map((item,index)=>item.receipt&&<div className="receipt-row" key={item.key}>
                  <strong>درخواست {index+1}</strong>
                  <span>نتیجه: <code dir="ltr">{item.receipt.disposition}</code></span>
                  <span>پیام کاربر: <code dir="ltr">{item.receipt.message_id??'null'}</code></span>
                  {item.answer&&<span>پیام پاسخ: <code dir="ltr">{item.answer.message_id}</code></span>}
                  {item.answer&&<span>شناسهٔ پاسخ: <code dir="ltr">{item.answer.answer_id}</code></span>}
                  <span>ردیابی تلاش: <code dir="ltr">{item.receipt.trace_id}</code></span>
                </div>)}
              </div>}
            </div>
          </details>
          <form className="composer" onSubmit={event=>{event.preventDefault();submit()}}>
            <label htmlFor="question" className="sr-only">متن پرسش فارسی</label>
            <textarea id="question" rows={Math.min(2,Math.max(1,draft.split('\n').length))}
              value={draft} disabled={!!activeKey}
              onChange={event=>setDraft(event.target.value)}
              onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.nativeEvent.isComposing){
                event.preventDefault();submit();
              }}} placeholder="سؤال خود را بنویسید…"/>
            <button type="submit" className="primary" disabled={!draft.trim()||!!activeKey}
              aria-label="ارسال پرسش">
              ارسال <span aria-hidden="true">←</span>
            </button>
          </form>
          <p className="under-composer">Enter برای ارسال · Shift+Enter برای سطر جدید</p>
        </div>
      </section>:<section className="placeholder-view" aria-labelledby="placeholder-heading">
        <p className="placeholder-eyebrow">نمای معرفی آزمایشی · فاز سوم</p>
        <h1 id="placeholder-heading">{view==='account'?'حساب کاربری':'حریم خصوصی'}</h1>
        <p className="placeholder-lead">{view==='account'
          ?'ورود و مدیریت حساب هنوز متصل نیست.'
          :'مدیریت رضایت و درخواست حذف در نسخهٔ متصل ارائه می‌شود.'}</p>
        <p className="placeholder-footnote">{view==='account'
          ?'در این نسخه حساب، پروفایل یا نشست کاربری ایجاد نمی‌شود.'
          :'هیچ رضایتی ثبت نشده و درخواست حذفی به سرور ارسال نمی‌شود.'}</p>
      </section>}
      </div>
    </div>
    {mobileMenuOpen&&<div className="mobile-nav-overlay">
      <button type="button" className="mobile-nav-scrim" aria-label="بستن منوی ناوبری"
        onClick={closeMobileMenu}/>
      <div id="mobile-navigation" ref={mobileDialogRef} tabIndex={-1}
        className="mobile-nav-dialog" role="dialog" aria-modal="true"
        aria-label="منوی ناوبری" onKeyDown={onMobileKeyDown}>
        <button ref={mobileCloseRef} className="mobile-close-button" type="button"
          aria-label="بستن منوی ناوبری" onClick={closeMobileMenu}>×</button>
        <Navigation view={view} collapsed={false} mobile hasConversation={hasConversation}
          conversationPreview={conversationPreview} onView={navigate} onNewChat={beginNewChat}/>
      </div>
    </div>}
    {drawer&&<SourceDrawer source={drawer.source} claim={drawer.claim} onClose={closeSource}/>}
  </main>
}
