'use client';
import type {EvidenceDisplayRow} from './retrieval-evidence-view';
import {classifyEvidence} from './retrieval-evidence-view';

/**
 * Render ONLY API-verified C018 evidence supplied by an approved,
 * authenticated, attempt-bound DTO. No caller in the product currently
 * supplies these rows; no synthetic fixture becomes a live citation.
 */
export default function RetrievalEvidencePanel(
 {rows}:{rows:readonly EvidenceDisplayRow[]}
){
  const positions=new Set(rows.map(row=>row.position));
  if(rows.length>10||positions.size!==rows.length||
     rows.some(row=>!Number.isSafeInteger(row.position)||row.position<1||
       row.position>10)){
    return <p role="alert" data-testid="retrieval-source-invalid">
      فهرست منابع قابل اعتبارسنجی نیست؛ منبعی به‌عنوان معتبر نمایش داده نمی‌شود.
    </p>;
  }
  return <section className="retrieval-evidence-list" data-testid="retrieval-evidence-list"
    aria-label="شواهد بازیابی بدون تولید پاسخ">
    <h3>شواهد بازیابی</h3>
    <p className="history-note">این موارد شاهد بازیابی هستند، نه استناد پاسخ تولیدشده.</p>
    <ol>
      {[...rows].sort((a,b)=>a.position-b.position).map(row=>{
        const decision=classifyEvidence(row);
        return <li key={row.position} className="product-citation">
          <span>رتبهٔ بازیابی: {row.position}</span>
          {decision.displayIdentifiers&&<>
            <span>شناسهٔ قطعه: <code dir="ltr">{row.chunkId}</code></span>
            <span>شناسهٔ منبع: <code dir="ltr">{row.sourceId}</code></span>
          </>}
          {decision.locationText&&<span>{decision.locationText}</span>}
          {decision.href?<a href={decision.href} target="_blank"
            rel="noopener noreferrer">{decision.label}</a>:
            <span role="status" className="history-note">{decision.label}</span>}
        </li>;
      })}
    </ol>
  </section>;
}
