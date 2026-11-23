'use client';
import type {RetrievedSources} from '../history/client';

/** Strictly observed, same-Attempt C018 retrieval rows.
 * Source attribution and locator validation are UNVERIFIED by the API v1.
 * Never render citations, URLs or anchors from this receipt.
 */
export default function RetrievedSourcesPanel({
  receipt,unavailable
}:{
  receipt:RetrievedSources|null;unavailable:boolean
}){
  if(unavailable)return <p role="alert" data-testid="retrieved-sources-unavailable"
    className="retrieval-evidence-status">
    خطا در دریافت یا اعتبارسنجی رسید منابع همین Attempt؛ هیچ منبعی تأیید نشده است.
  </p>;
  if(receipt===null)return <p role="status" data-testid="retrieved-sources-pending"
    className="retrieval-evidence-status">
    رسید مستقل منابع هنوز در دسترس نیست؛ نتیجهٔ بازیابی نامعلوم است.
  </p>;
  if(receipt.retrievalState!=='PARTIAL_UNVERIFIED'){
    const message={
      NOT_AVAILABLE:'هنوز بازیابی منابع برای این Attempt ثبت نشده است.',
      EVIDENCE_INVALID:'شواهد این Attempt اعتبارسنجی نشده‌اند؛ فهرست منابع مخفی است.',
      EVIDENCE_NOT_AVAILABLE:'رسید معتبر منابع این Attempt موجود نیست.'
    }[receipt.retrievalState];
    return <p role="status" className="retrieval-evidence-status"
      data-testid="retrieved-sources-empty">{message}</p>;
  }
  return <section className="retrieval-evidence-list product-evidence"
    aria-label="شواهد بازیابی فنی همین Attempt؛ استناد تأییدنشده"
    data-testid="retrieved-sources-observed">
    <h3>شواهد بازیابی — انتساب تأییدنشده</h3>
    <p className="history-note">این‌ها صرفاً شناسه‌های مشاهده‌شده در اجرای بازیابی هستند؛
      اعتبار منبع، مقصد و هرگونه Citation هنوز تأیید نشده است.</p>
    <p className="history-note">شناسهٔ Attempt: <code dir="ltr">{receipt.attemptId}</code></p>
    {receipt.rows.length===0
      ?<p role="status">قطعهٔ قابل‌نمایش در رسید ثبت نشده است.</p>
      :<ol>{receipt.rows.map(row=><li key={row.position} className="product-citation">
        <span>رتبهٔ بازیابی: {row.position}</span>
        <span>شناسهٔ قطعهٔ مشاهده‌شده: <code dir="ltr">{row.chunkId}</code></span>
        <span>شناسهٔ منبع مشاهده‌شده: <code dir="ltr">{row.sourceId??'ثبت نشده'}</code></span>
        <span className="history-note">Locator تأییدشده: ندارد؛ پیوند غیرفعال است.</span>
      </li>)}</ol>}
    <p className="history-note">هیچ پیوند یا استناد تأییدشده‌ای از این رسید ساخته نمی‌شود.</p>
  </section>;
}
