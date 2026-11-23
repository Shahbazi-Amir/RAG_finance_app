/** URL actions are derived exclusively from THIS LIVE_VERIFIED Answer's
 * verified Locator. A book anchor or transcript timestamp is never a URL.
 * No guessed hostname, source catalog lookup, or string-from-title fallback.
 */
import type {Source} from '../mock/transport';
import {publicHttpsUrl} from './public-https.ts';

export function verifiedSourceUrl(source:Source):string|null {
  if(source.resolution_status!=='verified'||
     source.attribution_status!=='verified'||
     source.display_title_origin==='SYNTHETIC'||
     source.locator?.kind!=='url'||!source.locator.url)return null;
  return publicHttpsUrl(source.locator.url);
}


/** Human-readable, non-navigating representation of a resolver-issued
 * physical locator. A book anchor or transcript segment NEVER becomes a URL.
 * Absent/unverified/mistyped metadata must yield no user-visible locator.
 */
export function verifiedSourceLocatorLabel(source:Source):string|null{
  if(source.resolution_status!=='verified'||
     source.attribution_status!=='verified'||
     source.display_title_origin==='SYNTHETIC'||
     typeof source.source_id!=='string'||!source.source_id.trim())return null;
  const loc=source.locator;
  if(!loc)return null;
  const present=(x:unknown):x is string=>typeof x==='string'&&x.trim().length>0;
  switch(loc.kind){
    case 'url':
      return source.source_type==='website'&&verifiedSourceUrl(source)
        ?'نشانی وب تأییدشده (پیوند قابل بازکردن)':null;
    case 'book_page':
      return source.source_type==='book'&&typeof loc.page==='number'&&
        Number.isSafeInteger(loc.page)&&loc.page>0
        ?'صفحهٔ ثبت‌شدهٔ کتاب: '+loc.page:null;
    case 'book_anchor':
      return source.source_type==='book'&&present(loc.work_id)&&
        present(loc.edition_id)&&present(loc.anchor)
        ?'نشانگر کتاب (غیرقابل کلیک) — اثر: '+loc.work_id+
          '؛ ویرایش: '+loc.edition_id+'؛ بخش: '+loc.anchor:null;
    case 'transcript_timestamp':
      return source.source_type==='transcript'&&
        typeof loc.timestamp_ms==='number'&&
        Number.isSafeInteger(loc.timestamp_ms)&&loc.timestamp_ms>=0
        ?'زمان ثبت‌شده در متن گفتار: '+loc.timestamp_ms+' میلی‌ثانیه':null;
    case 'transcript_segment':
      return source.source_type==='transcript'&&
        present(loc.episode_id)&&present(loc.segment_anchor)
        ?'بخش متن گفتار (غیرقابل کلیک) — قسمت: '+loc.episode_id+
          '؛ قطعه: '+loc.segment_anchor:null;
    default:return null;
  }
}

export function verifiedSourceTypeLabel(source:Source):string|null{
  if(verifiedSourceLocatorLabel(source)===null)return null;
  switch(source.source_type){
    case 'website':return 'وب‌سایت';
    case 'book':return 'کتاب';
    case 'transcript':return 'متن گفتار';
    default:return null;
  }
}
