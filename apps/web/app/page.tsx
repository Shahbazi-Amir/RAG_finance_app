'use client';
import { useEffect, useRef, useState } from 'react';
import {
  CONTRACT_VERSION,FIXTURE_ORIGIN,MockTransport,SCENARIOS,isRealSourceClaim,
  newRequest,safeSourceHref,terminalDisplay,
  type Answer,type Scenario,type SendReceipt,type SendRequest,type Source
} from '../src/mock/transport';

type Item={key:string;request:SendRequest;scenario:Scenario;receipt?:SendReceipt;
  text:string;answer?:Answer;phase:string;terminal?:string;isRunning:boolean;
  displayStopped?:boolean;warning?:string};
const scenarioNames:Record<Scenario,string>={
  answer:'پاسخ نمونه با منبع',partial:'پاسخ ناقص',no_answer:'بدون پاسخ',
  clarification:'نیازمند توضیح',refusal:'امتناع',error:'خطای فنی',
  unknown:'وضعیت نامعلوم',malicious:'آزمایش محتوای مخرب (امن)'
};
const outcomeNames:Record<string,string>={
  answer:'پاسخ نمونه',partial:'پاسخ ناقص — نه موفقیت کامل',
  no_answer:'بدون پاسخ',clarification:'درخواست توضیح',refusal:'امتناع',
  error:'خطای فنی',unknown:'نامعلوم — نتیجه تأیید نشده',cancelled:'لغوشده'
};
const phaseNames:Record<string,string>={
  submitting:'در حال ارسال محلی',connected:'اتصال گزارش‌شدهٔ Mock',
  retrieving:'بازیابی گزارش‌شدهٔ Mock',generating:'تولید گزارش‌شدهٔ Mock',
  delta:'در حال دریافت پاسخ نمونه',completed:'جریان پایان یافت',
  'display-stopped':'فقط نمایش متوقف شده؛ وضعیت سرور تأیید نشده',
  'cancel-requested':'درخواست توقف به سرور نمونه ارسال شد؛ تأیید نشده',
  'server-cancelled':'Mock توقف را تأیید کرد',failed:'خطای فنی نمونه',
  unknown:'نتیجهٔ Mock نامعلوم',conflict:'تعارض Idempotency؛ پیام ثبت نشد',
  replayed:'رسید بازپخش دریافت شد'
};
function SourceDrawer({source,claim,onClose}:{source:Source;claim:string;onClose:()=>void}){
  const closeRef=useRef<HTMLButtonElement>(null);
  useEffect(()=>{closeRef.current?.focus()},[]);
  const href=safeSourceHref(source);
  return <div className="drawer-backdrop" onClick={onClose}>
    <aside className="drawer" role="dialog" aria-modal="true" aria-label="جزئیات منبع نمونه"
      onClick={event=>event.stopPropagation()}>
      <div className="drawer-head"><h2>جزئیات منبع</h2>
        <button ref={closeRef} className="icon-button" onClick={onClose} aria-label="بستن پنل منبع">×</button>
      </div>
      <div className="hint">این منبع از Fixture مصنوعی است؛ اصالت و محل شاهد واقعی تأیید نشده‌اند.</div>
      <p className="eyebrow">ادعای مرتبط</p><p className="plain-value">{claim}</p>
      <dl className="source-meta">
        <dt>عنوان دریافت‌شده</dt>
        <dd>{source.display_title&&source.display_title_origin?source.display_title:'عنوانی ارائه نشده'}</dd>
        <dt>منشأ اعلام‌شدهٔ عنوان</dt><dd>{source.display_title_origin??'نامشخص'} — تأیید اصالت نیست</dd>
        <dt>نوع منبع</dt><dd>{source.source_type??'نامشخص'}</dd>
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
export default function HomePage(){
  const transport=useRef<MockTransport|null>(null);
  if(!transport.current)transport.current=new MockTransport();
  const [draft,setDraft]=useState('تفاوت پس‌انداز و سرمایه‌گذاری چیست؟');
  const [scenario,setScenario]=useState<Scenario>('answer');
  const [items,setItems]=useState<Item[]>([]);
  const [threadId,setThreadId]=useState<string|null>(null);
  const [activeKey,setActiveKey]=useState<string|null>(null);
  const [drawer,setDrawer]=useState<{source:Source;claim:string}|null>(null);
  const suppress=useRef(new Set<string>());
  const token=useRef(0);
  const endRef=useRef<HTMLDivElement>(null);
  useEffect(()=>{endRef.current?.scrollIntoView({block:'end',behavior:'smooth'})},[items.length]);
  function patch(key:string,part:Partial<Item>){
    setItems(old=>old.map(i=>i.key===key?{...i,...part}:i));
  }
  async function run(req:SendRequest,chosen:Scenario){
    const key=req.client_message_id,runId=++token.current;
    suppress.current.delete(key);
    setActiveKey(key);
    setItems(old=>old.some(i=>i.key===key)
      ?old.map(i=>i.key===key?{...i,phase:'submitting',isRunning:true,terminal:undefined,
        text:'',answer:undefined,warning:undefined,displayStopped:false}:i)
      :[...old,{key,request:req,scenario:chosen,phase:'submitting',text:'',isRunning:true}]);
    let cumulative='';
    try{
      for await(const u of transport.current!.send(req,chosen)){
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
            patch(key,{phase:'cancel-requested'});
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
    if(!active?.receipt)return;
    transport.current!.requestServerCancellation(active.receipt.request_id);
    patch(active.key,{phase:'cancel-requested'});
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
    setDrawer(null);setDraft('');transport.current=new MockTransport();
  }
  return <main className="app-shell" dir="rtl">
    <header className="topbar">
      <div className="brand"><span className="brand-mark" aria-hidden="true">ف</span>
        <div><strong>راگ مالی</strong><small>نمونهٔ رابط فاز سوم</small></div></div>
      <span className="demo-pill">نسخهٔ آزمایشی — پاسخ‌های نمونه</span>
    </header>
    <div className="workspace">
      <aside className="side-panel" aria-label="توضیح محیط آزمایشی">
        <p className="eyebrow">آزمایش مستقل L1</p>
        <h2>یادگیری مالی با پرسش و پاسخ</h2>
        <p>پرسش خود را وارد و مسیر دریافت پاسخ را با دادهٔ مصنوعی بررسی کنید. هیچ موتور، سرور یا پایگاه‌داده‌ای متصل نیست.</p>
        <div className="contract-note"><span>قرارداد</span><strong>{CONTRACT_VERSION}</strong>
          <span>منشأ</span><strong>{FIXTURE_ORIGIN}</strong></div>
        <button className="secondary wide" onClick={clearChat}>شروع گفتگوی آزمایشی تازه</button>
        <p className="side-foot">این نسخه مشاورهٔ مالی نیست؛ گفتگوها ذخیره نمی‌شوند.</p>
      </aside>
      <section className="chat-panel" aria-label="گفتگوی آزمایشی فارسی">
        <div className="chat-heading"><div><p className="eyebrow">محیط تست رابط</p>
          <h1>یک سؤال مالی بپرسید</h1><p>جریان رویدادها از Mock نسخه‌دار است، نه موتور واقعی.</p>
          </div><span className="online-pill">Mock · محلی</span></div>
        <div className="messages" aria-live="polite" aria-relevant="additions text">
          {!items.length&&<div className="empty-state">
            <span className="empty-icon" aria-hidden="true">✦</span><h2>گفتگو را شروع کنید</h2>
            <p>برای آزمایش پاسخ، پرسشی بنویسید و سناریوی موردنظر را انتخاب کنید.</p>
            <p className="empty-example">مثال: «چرا بودجه‌بندی ماهانه مهم است؟»</p></div>}
          {items.map(item=><article className="message-set" key={item.key}>
            <div className="user-bubble"><span className="message-label">شما · آزمایشی</span>
              <p>{item.request.question}</p></div>
            <div className="answer-bubble"><span className="message-label">دستیار نمونه
              <span className="sample-chip">SYNTHETIC</span></span>
              <div className="state-line" role="status">{phaseNames[item.phase]??item.phase}
                {item.receipt?.disposition==='replayed'?' · رسید بازپخش‌شده':''}</div>
              {item.terminal==='conflict'&&<p className="error-text">متن متفاوت با همان کلید رد شد؛ پیام جدید ثبت نشد.</p>}
              {item.text&&<p className="answer-text">{item.text}</p>}
              {item.answer&&<>
                <p className="outcome">{outcomeNames[item.answer.outcome]??'وضعیت تعریف‌نشده'}</p>
                {item.answer.confidence===null&&<p className="confidence">Confidence: اندازه‌گیری نشده (null)</p>}
                {item.answer.claims.map(claim=><div className="claim" key={claim.claim_id}>
                  <p><strong>ادعا:</strong> {claim.text}</p>
                  {claim.citation_ids.map(cid=>{
                    const c=item.answer!.citations.find(x=>x.citation_id===cid);
                    return c?<button className="source-button" key={cid}
                      onClick={()=>setDrawer({source:c.source,claim:claim.text})}>
                      مشاهدهٔ منبع آزمایشی <span aria-hidden="true">↗</span></button>:null;
                  })}
                </div>)}
              </>}
              {item.warning&&<p className="error-text">{item.warning}</p>}
              {item.displayStopped&&<p className="warning">فقط نمایش متوقف شد؛ توقف سرور ثابت نشده است.</p>}
              {['partial','unknown','failed'].includes(item.terminal??'')&&
                <p className="warning">این وضعیت پاسخ کامل و تأییدشده نیست.</p>}
              {item.receipt&&<p className="receipt-label">رسید Mock: {item.receipt.disposition} · {item.receipt.message_id??'بدون پیام'}</p>}
            </div>
          </article>)}
          <div ref={endRef}/>
        </div>
        <div className="chat-footer">
          {active&&<div className="run-controls">
            <button className="secondary" onClick={cancelDisplay}>توقف نمایش (نه موتور)</button>
            <button className="secondary" disabled={!active.receipt||
              transport.current?.hasRequestedServerCancellation(active.receipt?.request_id??'')}
              onClick={cancelServer}>درخواست لغو به سرور نمونه</button>
          </div>}
          {!activeKey&&items.length>0&&<div className="run-controls">
            <button className="secondary" onClick={()=>retryLatest()}>ارسال مجدد با همان شناسه</button>
            <button className="secondary" onClick={()=>retryLatest(true)}>آزمایش Conflict</button>
          </div>}
          <div className="compose-tools"><label htmlFor="scenario">سناریوی پاسخ</label>
            <select id="scenario" value={scenario}
              onChange={e=>setScenario(e.target.value as Scenario)} disabled={!!activeKey}>
              {SCENARIOS.map(k=><option key={k} value={k}>{scenarioNames[k]}</option>)}</select></div>
          <form className="composer" onSubmit={e=>{e.preventDefault();submit()}}>
            <label htmlFor="question" className="sr-only">متن پرسش فارسی</label>
            <textarea id="question" rows={2} value={draft}
              disabled={!!activeKey} onChange={e=>setDraft(e.target.value)}
              onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){
                e.preventDefault();submit();
              }}} placeholder="پرسش آزمایشی را اینجا بنویسید…"/>
            <button type="submit" className="primary" disabled={!draft.trim()||!!activeKey}>
              ارسال پرسش <span aria-hidden="true">←</span></button>
          </form>
          <p className="under-composer">Enter: ارسال · Shift+Enter: خط جدید · فقط حافظهٔ صفحه</p>
        </div>
      </section>
    </div>
    {drawer&&<SourceDrawer source={drawer.source} claim={drawer.claim} onClose={()=>setDrawer(null)}/>}
  </main>
}
