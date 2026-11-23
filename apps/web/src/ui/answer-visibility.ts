/** Product-rendering gate. Technical states are not "no evidence".
 * No fixture/provisional output is a user-facing live Answer.
 * Source quoting remains unavailable in product.v1; don't fabricate it.
 */
import type {Answer} from '../mock/transport';

export function isVerifiedLiveAnswer(answer:Answer|null):answer is Answer {
  return answer!==null&&answer.provenance.origin==='LIVE_VERIFIED'&&
    answer.provenance.rag_binding.status==='verified'&&
    answer.provenance.rag_binding.adapter_verified===true;
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
