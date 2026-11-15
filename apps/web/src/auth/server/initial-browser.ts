/** Isolated HTTPS-browser policy; never silently permits production HTTP. */
import {createHmac,randomBytes,timingSafeEqual} from 'node:crypto';
export const INIT='__Host-rag-login-init';
export const SESSION='__Host-rag-session';
const err=():never=>{throw new Error('AUTH_BROWSER_POLICY_DENIED');};
export function publicOrigin():string{
  if(process.env.CI!=='true')err();
  const origin=process.env.AUTH_CI_PUBLIC_ORIGIN??'';
  let url:URL;
  try{url=new URL(origin);}catch{return err();}
  if(url.protocol!=='https:'||url.hostname!=='127.0.0.1'||
      !url.port||url.pathname!=='/'||url.search||url.hash)err();
  return origin;
}
export function secureBrowser(request:Request):boolean{
  try{
    publicOrigin();
    // Only isolated private-loopback Next instance may receive requests from
    // a trusted TLS termination proxy. Direct HTTP never satisfies this guard.
    const expected=process.env.AUTH_CI_PROXY_SECRET??'';
    const supplied=request.headers.get('x-auth-ci-proxy-proof')??'';
    return expected.length>=32&&supplied.length===expected.length&&
      timingSafeEqual(Buffer.from(expected),Buffer.from(supplied));
  }catch{return false;}
}
export function csrf(initiator:string):string{
  const secret=process.env.AUTH_CI_CSRF_SECRET??'';
  if(secret.length<32||!/^[A-Za-z0-9_-]{32,256}$/.test(initiator))err();
  return createHmac('sha256',secret).update('csrf-login-v1:').update(initiator)
    .digest('base64url');
}
export const freshCookie=()=>randomBytes(32).toString('base64url');
export function same(a:string,b:string):boolean{
  if(!a||!b||a.length!==b.length)return false;
  return timingSafeEqual(Buffer.from(a),Buffer.from(b));
}
export function cookie(request:Request,name:string):string|null{
  const found=(request.headers.get('cookie')??'').split(';').map(x=>x.trim())
    .filter(x=>x.startsWith(name+'='));
  if(found.length!==1)return null;
  const value=found[0].slice(name.length+1);
  return /^[A-Za-z0-9_-]{32,256}$/.test(value)?value:null;
}
export function mutationAllowed(request:Request,token:string,expected:string):boolean{
  if(!secureBrowser(request)||request.headers.get('origin')!==publicOrigin()||
     request.headers.get('sec-fetch-site')!=='same-origin')return false;
  return same(token,expected);
}
export function appendCookie(response:Response,name:string,value:string,maxAge:number){
  const token=value?name+'='+value:name+'=';
  response.headers.append('Set-Cookie',token+
    '; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age='+maxAge);
}
export const noStore={'Cache-Control':'no-store','Referrer-Policy':'no-referrer',
  'X-Content-Type-Options':'nosniff'};
export function redirectLocal(path:string):Response{
  const target=new URL(path,publicOrigin());
  return new Response(null,{status:303,headers:{...noStore,Location:target.toString()}});
}
