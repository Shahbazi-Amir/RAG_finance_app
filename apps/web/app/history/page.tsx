'use client';
import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import Link from 'next/link';
import {
  conversations,messages,createConversation,newCreate,newSend,sendMessage,recoverStatus,
  mergeUnique,HistoryFailure,failureLabel,
  type ConversationView,type MessageView,type AnswerView,type CreateOperation,type PendingSend
} from '../../src/history/client';
import './history.css';

type ListState='loading'|'loaded'|'empty'|'error'|'unauthorized';
type ThreadData={items:MessageView[];answers:AnswerView[];next:string|null;more:boolean;phase:ListState};
const emptyThread=():ThreadData=>({items:[],answers:[],next:null,more:false,phase:'loading'});
type PendingCreate={origin:string;request:CreateOperation;phase:'unknown'|'submitting'};

export default function HistoryPage(){
  // Nothing private is written to browser storage or log. Reload reads PostgreSQL.
  const [list,setList]=useState<ConversationView[]>([]);
  const [listState,setListState]=useState<ListState>('loading');
  const [listCursor,setListCursor]=useState<string|null>(null);
  const [listMore,setListMore]=useState(false);
  const [listBusy,setListBusy]=useState(false);
  const [selected,setSelected]=useState<string|null>(null);
  const [drafts,setDrafts]=useState<Record<string,string>>({});
  const [threads,setThreads]=useState<Record<string,ThreadData>>({});
  const [pending,setPending]=useState<Record<string,PendingSend[]>>({});
  const [busy,setBusy]=useState<Record<string,boolean>>({});
  const [creating,setCreating]=useState<PendingCreate|null>(null);
  const [error,setError]=useState('');
  const [mobileMenuOpen,setMobileMenuOpen]=useState(false);
  const mobileTriggerRef=useRef<HTMLButtonElement>(null);
  const mobileCloseRef=useRef<HTMLButtonElement>(null);
  const mobileDialogRef=useRef<HTMLElement>(null);
  const epochs=useRef<Record<string,number>>({});
  useEffect(()=>{
    if(!mobileMenuOpen)return;
    const previousOverflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    mobileCloseRef.current?.focus();
    return ()=>{document.body.style.overflow=previousOverflow;};
  },[mobileMenuOpen]);
  function closeMobileMenu(){
    setMobileMenuOpen(false);
    window.requestAnimationFrame(()=>mobileTriggerRef.current?.focus());
  }
  function onMobileKeyDown(event:ReactKeyboardEvent<HTMLElement>){
    if(!mobileMenuOpen)return;
    if(event.key==='Escape'){
      event.preventDefault();event.stopPropagation();closeMobileMenu();return;
    }
    if(event.key!=='Tab')return;
    const dialog=mobileDialogRef.current;
    if(!dialog)return;
    const focusable=Array.from(dialog.querySelectorAll<HTMLElement>(
      'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
    )).filter(element=>element.getClientRects().length>0);
    if(!focusable.length){event.preventDefault();dialog.focus();return;}
    const first=focusable[0],last=focusable[focusable.length-1];
    if(event.shiftKey&&(document.activeElement===first||!dialog.contains(document.activeElement))){
      event.preventDefault();last.focus();
    }else if(!event.shiftKey&&(document.activeElement===last||!dialog.contains(document.activeElement))){
      event.preventDefault();first.focus();
    }
  }

  const loadList=useCallback(async (next=false,cursor:string|null=null)=>{
    setListBusy(true);
    if(!next)setListState('loading');
    try{
      const page=await conversations(2,next?cursor:null);
      setList(prev=>next?mergeUnique(prev,page.items,x=>x.id):page.items);
      setListCursor(page.next);setListMore(page.more);
      setListState(page.items.length===0&&!next?'empty':'loaded');
      if(!next)setSelected(old=>old??(page.items[0]?.id??'draft:new'));
      setError('');
    }catch(e){
      setListState(e instanceof HistoryFailure&&e.reason==='unauthorized'?'unauthorized':'error');
      setError(failureLabel(e));
    }finally{setListBusy(false);}
  },[]);
  const loadThread=useCallback(async (id:string,next=false,cursor:string|null=null)=>{
    const epoch=(epochs.current[id]??0)+1;epochs.current[id]=epoch;
    setThreads(all=>({...all,[id]:{...(all[id]??emptyThread()),phase:'loading'}}));
    try{
      const page=await messages(id,2,next?cursor:null);
      if(epochs.current[id]!==epoch)return;
      setThreads(all=>{
        const prior=all[id]??emptyThread();
        return {...all,[id]:{
          items:next?mergeUnique(prior.items,page.items,x=>x.id):page.items,
          answers:next?mergeUnique(prior.answers,page.answers,x=>x.id):page.answers,
          next:page.next,more:page.more,
          phase:page.items.length===0&&!next?'empty':'loaded'
        }};
      });
      setError('');
    }catch(e){
      if(epochs.current[id]!==epoch)return;
      setThreads(all=>({...all,[id]:{...(all[id]??emptyThread()),
        phase:e instanceof HistoryFailure&&e.reason==='unauthorized'?'unauthorized':'error'}}));
      setError(failureLabel(e));
    }
  },[]);
  useEffect(()=>{void loadList();},[loadList]);
  // Refresh selects the first server thread after the list arrives. Load its
  // messages even when the user has not clicked a list row yet.
  useEffect(()=>{
    if(selected&&!selected.startsWith('draft:')&&!threads[selected])void loadThread(selected);
  },[selected,threads,loadThread]);
  function choose(id:string){
    setSelected(id);setError('');
    if(!id.startsWith('draft:'))void loadThread(id);
    if(mobileMenuOpen)closeMobileMenu();
  }
  function newDraft(){const id='draft:'+crypto.randomUUID();setDrafts(all=>({...all,[id]:''}));choose(id);}
  function mark(origin:string,key:string,patch:Partial<PendingSend>){
    setPending(all=>({...all,[origin]:(all[origin]??[]).map(p=>
      p.request.client_message_id===key?{...p,...patch}:p)}));
  }
  function confirmed(origin:string,request:PendingSend['request'],id:string,messageId:string){
    setPending(all=>{
      const prev=all[origin]??[];
      const updated=prev.map(p=>p.request.client_message_id===request.client_message_id
        ?{...p,phase:'persisted' as const,serverId:id,messageId}:p);
      if(origin===id)return {...all,[origin]:updated};
      return {...all,[origin]:[],[id]:mergeUnique(all[id]??[],updated,x=>x.request.client_message_id)};
    });
    setSelected(now=>now===origin?id:now); // never steal focus from a later-selected chat
    setDrafts(all=>origin===id?all:{...all,[id]:all[origin]??'', [origin]:''});
    void loadList();
    void loadThread(id);
  }
  async function submitMessage(event:FormEvent<HTMLFormElement>){
    event.preventDefault();
    const origin=selected;
    if(!origin||busy[origin])return;
    const question=(drafts[origin]??'').trim();
    if(!question)return;
    const originalId=origin.startsWith('draft:')?null:origin;
    const request=newSend(question,originalId);
    setPending(all=>({...all,[origin]:[...(all[origin]??[]),
      {request,phase:'sending',serverId:null,messageId:null}]}));
    setBusy(all=>({...all,[origin]:true}));
    setDrafts(all=>({...all,[origin]:''}));setError('');
    try{
      const receipt=await sendMessage(request);
      confirmed(origin,request,receipt.id,receipt.messageId);
    }catch(e){
      mark(origin,request.client_message_id,{
        phase:e instanceof HistoryFailure&&e.reason==='conflict'?'conflict'
          :e instanceof HistoryFailure&&e.reason==='unauthorized'?'unauthorized':'unknown'
      });
      setError(failureLabel(e));
    }finally{setBusy(all=>({...all,[origin]:false}));}
  }
  async function repeat(origin:string,item:PendingSend){
    if(busy[origin])return;
    setBusy(all=>({...all,[origin]:true}));
    mark(origin,item.request.client_message_id,{phase:'sending'});
    try{
      const receipt=await sendMessage(item.request); // original null/id/key/question unchanged
      confirmed(origin,item.request,receipt.id,receipt.messageId);
    }catch(e){
      mark(origin,item.request.client_message_id,{
        phase:e instanceof HistoryFailure&&e.reason==='conflict'?'conflict':'unknown'
      });
      setError(failureLabel(e));
    }finally{setBusy(all=>({...all,[origin]:false}));}
  }
  async function recover(origin:string,item:PendingSend){
    try{
      const status=await recoverStatus(item.request); // one read, no polling loop or T2
      if(status.status==='not_found'||!status.id||!status.messageId){
        mark(origin,item.request.client_message_id,{phase:'unconfirmed'});
        return;
      }
      confirmed(origin,item.request,status.id,status.messageId);
    }catch(e){setError(failureLabel(e));}
  }
  async function performCreate(operation:PendingCreate){
    if(creating?.phase==='submitting')return;
    setCreating({...operation,phase:'submitting'});
    setError('');
    try{
      const id=await createConversation(operation.request);
      setCreating(null);
      setSelected(now=>now===operation.origin?id:now);
      void loadList();void loadThread(id);
    }catch(e){
      setCreating({...operation,phase:'unknown'});
      setError(failureLabel(e));
    }
  }
  function beginCreate(){
    if(mobileMenuOpen)closeMobileMenu();
    const origin=selected?.startsWith('draft:')?selected:'draft:'+crypto.randomUUID();
    const operation={origin,request:newCreate('گفت‌وگوی جدید'),phase:'submitting' as const};
    if(selected!==origin)setSelected(origin);
    void performCreate(operation);
  }
  const active=selected??'draft:new';
  const selectedServer=!active.startsWith('draft:');
  const data=selectedServer?threads[active]:undefined;
  const localItems=pending[active]??[];
  const renderedIds=new Set(data?.items.map(x=>x.id)??[]);
  const pendingVisible=localItems.filter(x=>!x.messageId||!renderedIds.has(x.messageId));
  const answersByMessage=new Map((data?.answers??[]).map(a=>[a.messageId,a.payload]));
  return <main className="history-shell" dir="rtl">
    {mobileMenuOpen&&<button type="button" className="history-mobile-scrim"
      aria-label="بستن منوی تاریخچه" onClick={closeMobileMenu}/>}
    <aside id="history-navigation" className={'history-sidebar'+(mobileMenuOpen?' is-mobile-open':'')}
      ref={mobileDialogRef} tabIndex={mobileMenuOpen?-1:undefined}
      role={mobileMenuOpen?'dialog':undefined}
      aria-modal={mobileMenuOpen?'true':undefined}
      aria-label={mobileMenuOpen?'منوی تاریخچه':'فهرست تاریخچه'}
      onKeyDown={onMobileKeyDown}>
      <button type="button" ref={mobileCloseRef} className="history-mobile-close"
        aria-label="بستن منوی تاریخچه" onClick={closeMobileMenu}>×</button>
      <div className="history-brand"><span className="brand-mark" aria-hidden="true">ف</span>
        <strong>راگ مالی</strong></div>
      <div className="history-actions">
        <button className="nav-new-chat" data-testid="create-conversation" type="button"
          disabled={creating?.phase==='submitting'} onClick={beginCreate}>ایجاد مکالمه</button>
        <button className="secondary" data-testid="new-draft" type="button" onClick={newDraft}>شروع با پیام جدید</button>
        {creating?.phase==='unknown'&&<button className="secondary" type="button"
          data-testid="retry-create" onClick={()=>void performCreate(creating)}>تلاش دوباره با همان شناسه</button>}
      </div>
      <p className="nav-section-title">تاریخچهٔ ثبت‌شده در API</p>
      <div data-testid="history-state" role="status" className="history-state">
        {listState==='loading'?'در حال بارگذاری تاریخچه…'
          :listState==='empty'?'هنوز مکالمه‌ای ثبت نشده است.'
          :listState==='error'?'خطای دریافت تاریخچه'
          :listState==='unauthorized'?'ورود معتبر لازم است؛ ورود هنوز فراهم نیست.':''}
      </div>
      <nav aria-label="مکالمات ثبت‌شده" className="history-list">
        {list.map(c=>{
          const title=c.title??'گفت‌وگوی بدون عنوان';
          // Only validated, already loaded message pages may supply a preview.
          // Do not fetch each conversation to populate navigation labels.
          const preview=threads[c.id]?.items.find(m=>m.role==='user')?.text;
          const marker=c.title==='گفت‌وگوی جدید'
            ?preview?'پرسش: '+preview.slice(0,46):'شناسه: '+c.id.slice(-8)
            :null;
          return <button key={c.id} type="button" data-testid={'conversation-'+c.id}
            className={'nav-thread'+(selected===c.id?' is-current':'')}
            aria-current={selected===c.id?'page':undefined}
            aria-label={'بازکردن '+title+'؛ شناسهٔ کامل '+c.id+(preview?'؛ پرسش: '+preview:'')}
            onClick={()=>choose(c.id)}>
            <span className="nav-thread-text history-thread-title">{title}</span>
            {marker&&<span className="history-thread-detail" data-testid={'conversation-marker-'+c.id}>
              {marker}
            </span>}
          </button>;
        })}
      </nav>
      {listMore&&<button type="button" className="secondary" data-testid="more-conversations"
        disabled={listBusy} onClick={()=>void loadList(true,listCursor)}>
        نمایش مکالمه‌های بیشتر
      </button>}
      <button type="button" className="secondary" data-testid="refresh-history"
        disabled={listBusy} onClick={()=>void loadList()}>بازخوانی تاریخچه</button>
      <div className="history-sidebar-bottom">
        <Link href="/" className="history-link" data-testid="mock-link">بازگشت به Mock مستقل</Link>
        <p className="nav-local-notice">Mock در پایگاه داده ثبت نمی‌شود.</p>
      </div>
    </aside>
    <section className="history-main" aria-label="گفت‌وگوی تاریخچه">
      <header className="history-mobile-topbar">
        <button type="button" ref={mobileTriggerRef} className="mobile-menu-trigger"
          aria-label="بازکردن منوی تاریخچه" aria-haspopup="dialog"
          aria-controls="history-navigation" aria-expanded={mobileMenuOpen}
          onClick={()=>setMobileMenuOpen(true)}>
          <span aria-hidden="true">☰</span>
        </button>
        <span className="mobile-brand">راگ مالی</span>
        <span className="history-mobile-caption">تاریخچه</span>
      </header>
      <header className="history-heading">
        <h1>تاریخچهٔ گفتگو</h1><p>فقط ثبت و بازیابی پیام؛ پاسخ‌گویی موتور هنوز فعال نیست.</p>
      </header>
      {error&&<p role="alert" data-testid="history-error" className="history-error">{error}</p>}
      <div className="history-messages" aria-live="polite">
        {!selectedServer&&<p data-testid="draft-empty" className="history-empty">پرسش جدید را بنویسید یا مکالمه بسازید؛ شناسهٔ محلی، شناسهٔ سرور نیست.</p>}
        {selectedServer&&(!data||data.phase==='loading')&&<p data-testid="messages-loading">در حال بارگذاری پیام‌ها…</p>}
        {selectedServer&&data?.phase==='empty'&&<p data-testid="messages-empty">پیامی در این مکالمه ثبت نشده است.</p>}
        {selectedServer&&data?.phase==='error'&&<p data-testid="messages-error">دریافت پیام‌ها با خطا مواجه شد.</p>}
        {selectedServer&&data?.phase==='unauthorized'&&<p data-testid="messages-unauthorized">ورود معتبر برای تاریخچه لازم است.</p>}
        {(data?.items??[]).map(m=>{
          const answer=answersByMessage.get(m.id);
          return <article data-testid={'history-message-'+m.id} key={m.id}
            className={m.role==='user'?'history-user':'history-answer'}>
            <p className="history-message-text">{m.role==='assistant'&&answer&&answer.answer_text
              ?answer.answer_text:m.text}</p>
            {m.role==='user'&&<p className="history-note">پیام ثبت شد؛ پاسخ‌گویی موتور هنوز فعال نیست.</p>}
            {m.role==='assistant'&&<p className="history-note">
              {answer?'پاسخ از تاریخچهٔ معتبر API دریافت شده است.':'پیام دستیار در تاریخچهٔ API'}</p>}
          </article>;
        })}
        {pendingVisible.map(p=><article key={p.request.client_message_id}
          data-testid={'pending-'+p.request.client_message_id} className="history-user">
          <p className="history-message-text">{p.request.question}</p>
          <p className="history-note" role="status">
            {p.phase==='persisted'?'پیام ثبت شد؛ پاسخ‌گویی موتور هنوز فعال نیست.'
            :p.phase==='sending'?'در حال ثبت پیام…'
            :p.phase==='unknown'?'نتیجهٔ شبکه نامعلوم است؛ ثبت پیام تأیید نشده.'
            :p.phase==='unconfirmed'?'هنوز شاهدی از ثبت پیام پیدا نشد؛ شکست قطعی نیست.'
            :p.phase==='conflict'?'تعارض؛ ثبت جدید تأیید نشده.'
            :'ورود معتبر لازم است.'}
          </p>
          {(p.phase==='unknown'||p.phase==='unconfirmed')&&<div className="history-recovery">
            <button type="button" className="secondary" data-testid="recover-status"
              onClick={()=>void recover(active,p)}>بازیابی وضعیت</button>
            <button type="button" className="secondary" data-testid="retry-send" disabled={busy[active]}
              onClick={()=>void repeat(active,p)}>تکرار همان درخواست</button>
          </div>}
        </article>)}
        {data?.more&&<button className="secondary" data-testid="more-messages" type="button"
          disabled={data.phase==='loading'}
          onClick={()=>void loadThread(active,true,data.next)}>نمایش پیام‌های بیشتر</button>}
      </div>
      <form className="history-compose" onSubmit={event=>void submitMessage(event)}>
        <label htmlFor="history-question" className="sr-only">متن پرسش</label>
        <div className="composer">
          <textarea id="history-question" data-testid="history-question" rows={2}
            value={drafts[active]??''} placeholder="پرسش را اینجا بنویسید"
            onChange={event=>setDrafts(all=>({...all,[active]:event.target.value}))}
            disabled={listState==='unauthorized'} />
          <button className="primary" data-testid="history-send" type="submit"
            disabled={Boolean(busy[active])||listState==='unauthorized'||!(drafts[active]??'').trim()}>
            ثبت پیام
          </button>
        </div>
        <p className="under-composer">فقط تاریخچه در PostgreSQL ثبت می‌شود؛ هیچ پرسشی به موتور ارسال نمی‌شود.</p>
      </form>
    </section>
  </main>;
}
