/** Product rendering gate: technical retrieval is never a real Answer.
 * LIVE_VERIFIED provenance alone is insufficient for displaying factual
 * claims if the cited source/locator remains unverified or synthetic.
 * This is consumer defense-in-depth, not a substitute for server Claim checks.
 */
import type {Answer,Source} from '../mock/transport';
import {verifiedSourceUrl} from './source-locator.ts';

function nonempty(v:unknown):v is string{
  return typeof v==='string'&&v.trim().length>0;
}
function trustedCitationSource(source:Source):boolean{
  if(source.resolution_status!=='verified'||source.attribution_status!=='verified'||
     source.display_title_origin==='SYNTHETIC'||!nonempty(source.source_id))return false;
  const loc=source.locator;
  if(!loc)return false;
  switch(loc.kind){
    case 'url':return verifiedSourceUrl(source)!==null;
    case 'book_page':return Number.isSafeInteger(loc.page)&&loc.page!>0;
    case 'book_anchor':return nonempty(loc.work_id)&&
      nonempty(loc.edition_id)&&nonempty(loc.anchor);
    case 'transcript_timestamp':return Number.isSafeInteger(loc.timestamp_ms)&&
      loc.timestamp_ms!>=0;
    case 'transcript_segment':return nonempty(loc.episode_id)&&
      nonempty(loc.segment_anchor);
    default:return false;
  }
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
