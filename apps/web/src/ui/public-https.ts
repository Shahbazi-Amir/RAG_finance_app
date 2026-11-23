/** Defense-in-depth for API-verified public web destinations only.
 * A syntactically HTTPS URL does NOT itself prove source provenance or
 * authorization; callers must independently verify their source/locator.
 * DNS rebinding cannot be settled client-side and remains an API/Ops check.
 */
export function publicHttpsUrl(raw:string):string|null {
  if(typeof raw!=='string'||!raw||raw.trim()!==raw||raw.includes('\\'))return null;
  try{
    const url=new URL(raw);
    const host=url.hostname.toLowerCase();
    if(url.protocol!=='https:'||!host.includes('.')||
       url.username||url.password||url.port||url.hash||
       host==='localhost'||host.endsWith('.localhost')||
       ['.local','.internal','.test','.invalid','.example'].some(s=>host.endsWith(s))||
       /^\d+\.\d+\.\d+\.\d+$/.test(host)||host.startsWith('['))return null;
    return url.href;
  }catch{return null;}
}
