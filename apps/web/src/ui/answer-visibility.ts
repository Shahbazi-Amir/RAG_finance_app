/** Product rendering gate: technical retrieval is never a real Answer.
 * LIVE_VERIFIED provenance alone is insufficient for displaying factual
 * claims if the cited source/locator remains unverified or synthetic.
 * This is consumer defense-in-depth, not a substitute for server Claim checks.
 */
import type {Answer,Source} from '../mock/transport';
import {verifiedSourceLocatorLabel} from './source-locator.ts';

function trustedCitationSource(source:Source):boolean{
  return verifiedSourceLocatorLabel(source)!==null;
}
export function isVerifiedLiveAnswer(answer:Answer|null):answer is Answer {
  if(answer===null||answer.provenance.origin!=='LIVE_VERIFIED'||
     answer.provenance.rag_binding.status!=='verified'||
     answer.provenance.rag_binding.adapter_verified!==true)return false;
  // A no-answer, clarification or refusal may be a verified, citable-free
  // outcome. A factual answer or partial claim needs claim-level evidence.
  if(answer.outcome!=='answer'&&answer.outcome!=='partial')return true;
  if(!answer.claims.length||!answer.citations.length)return false;
  const citations=new Map(answer.citations.map(c=>[c.citation_id,c]));
  if(citations.size!==answer.citations.length)return false;
  return answer.claims.every(claim=>
    claim.citation_ids.length>0&&claim.citation_ids.every(id=>{
      const cite=citations.get(id);
      return cite!==undefined&&cite.claim_ids.includes(claim.claim_id)&&
        trustedCitationSource(cite.source);
    }));
}
export function productOutcomeLabel(answer:Answer):string {
  switch(answer.outcome){
    case 'answer':return '';
    case 'no_answer':return 'شاهد کافی برای پاسخ یافت نشد.';
    case 'partial':return 'پاسخ ناقص است.';
    case 'clarification':return 'برای پاسخ دقیق‌تر پرسش را روشن‌تر کنید.';
    case 'refusal':return 'پاسخ‌گویی به این پرسش ممکن نیست.';
    case 'error':return 'پاسخ با خطای فنی مواجه شده است.';
    default:return 'نتیجهٔ پاسخ نامعلوم است.';
  }
}
