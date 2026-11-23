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
