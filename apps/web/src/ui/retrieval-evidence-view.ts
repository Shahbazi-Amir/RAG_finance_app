/**
 * UI-only presentation policy for C018 retrieval rows.
 *
 * This is NOT an API wire contract. Only API_F3 may approve/verify the
 * source provenance and original member_locators. No raw C018 result or
 * Fixture is promoted to a verified Product Answer or source by this file.
 *
 * The C018 source-bearing endpoint/DTO is not yet approved. Do not wire
 * these cards to technical engine-status.top10_count or to synthetic demo.
 */
import {publicHttpsUrl} from './public-https.ts';

export type EvidenceLocator=
  |Readonly<{kind:'url';url:string;verified:boolean}>
  |Readonly<{kind:'book_page';page:number;verified:boolean}>
  |Readonly<{kind:'transcript_timestamp';timestampMs:number;verified:boolean}>
  |null;

export type EvidenceDisplayRow=Readonly<{
  position:number;chunkId:string;sourceId:string;
  sourceVerified:boolean;locator:EvidenceLocator;
}>;

export type EvidenceDecision=Readonly<{
  status:'unverified_source'|'unverified_destination'|'no_web_locator'|'verified_link';
  label:string;href:string|null;locationText:string|null;
  displayIdentifiers:boolean;
}>;

const reject=(status:EvidenceDecision['status'],label:string,
  displayIdentifiers:boolean):EvidenceDecision=>
  ({status,label,href:null,locationText:null,displayIdentifiers});

/** Never create an href from a chunk_id/title, and never trust a locator
 * merely because it is syntactically HTTPS.
 */
export function classifyEvidence(row:EvidenceDisplayRow):EvidenceDecision{
  if(!row.sourceVerified)
    return reject('unverified_source','منبع تأیید نشده؛ قابل استناد نیست.',false);
  if(!Number.isSafeInteger(row.position)||row.position<1||
     row.position>10||!row.chunkId||!row.sourceId)
    return reject('unverified_source','شناسه یا رتبهٔ منبع معتبر نیست.',false);
  const locator=row.locator;
  if(locator===null)
    return reject('no_web_locator','این منبع پیوند وب معتبر ندارد.',true);
  if(!locator.verified)
    return reject('unverified_destination','مقصد تأیید نشده؛ پیوند غیرفعال است.',true);
  if(locator.kind==='url'){
    const href=publicHttpsUrl(locator.url);
    return href?
      {status:'verified_link',label:'بازکردن مقصد تأییدشده',
        href,locationText:null,displayIdentifiers:true}:
      reject('unverified_destination','مقصد تأیید نشده؛ پیوند غیرفعال است.',true);
  }
  if(locator.kind==='book_page'){
    return Number.isSafeInteger(locator.page)&&locator.page>0?
      {status:'no_web_locator',label:'این منبع پیوند وب معتبر ندارد.',
        href:null,locationText:'صفحهٔ ثبت‌شده: '+locator.page,displayIdentifiers:true}:
      reject('unverified_destination','مکان منبع تأیید نشده است.',true);
  }
  if(locator.kind==='transcript_timestamp'){
    return Number.isSafeInteger(locator.timestampMs)&&locator.timestampMs>=0?
      {status:'no_web_locator',label:'این منبع پیوند وب معتبر ندارد.',
        href:null,locationText:'زمان ثبت‌شده (میلی‌ثانیه): '+locator.timestampMs,
        displayIdentifiers:true}:
      reject('unverified_destination','مکان منبع تأیید نشده است.',true);
  }
  return reject('unverified_destination','مقصد تأیید نشده؛ پیوند غیرفعال است.',true);
}
