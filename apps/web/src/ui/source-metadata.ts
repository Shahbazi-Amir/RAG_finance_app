/** Explicit, non-inferred display of resolver-issued fields. Distinct roles
 * are never substituted. Only a verified attribution on a verified source
 * may be credited. This does NOT turn retrieved-source rows into citations.
 */
import type {Source,Answer} from '../mock/transport';

export type SourceCredit=Readonly<{
  role:'author'|'editor'|'speaker';label:string;name:string
}>;
export function sourceCredits(source:Source):readonly SourceCredit[]{
  if(source.resolution_status!=='verified'||
     source.attribution_status!=='verified'||
     source.display_title_origin==='SYNTHETIC')return [];
  const out:SourceCredit[]=[];
  const entries=[
    ['author','نویسندهٔ ثبت‌شده',source.credited_author_name],
    ['editor','سردبیر ثبت‌شده',source.editorial_supervisor_name],
    ['speaker','گویندهٔ ثبت‌شده',source.speaker_name]
  ] as const;
  for(const [role,label,name] of entries)
    if(typeof name==='string'&&name.trim())out.push({role,label,name});
  return out;
}
export function confidenceLabel(answer:Answer):string {
  const c=answer.confidence;
  if(c===null)return 'میزان اطمینان کالیبره‌شده برای این پاسخ گزارش نشده است.';
  // product.v1 validates value in [0,1]. Never invent a percentage,
  // calibration or classification from an untrusted number.
  if(typeof c.meaning!=='string'||!c.meaning.trim()||
     typeof c.calibration_scope!=='string'||!c.calibration_scope.trim()||
     !Number.isFinite(c.value)||c.value<0||c.value>1)
    return 'میزان اطمینان قابل گزارش نیست.';
  return 'توصیف اطمینان ثبت‌شده: '+c.meaning+
    '؛ دامنهٔ کالیبراسیون ثبت‌شده: '+c.calibration_scope;
}
