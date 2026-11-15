/**
 * Explicit fail-closed Logout boundary.
 * API #48 exposes START/COMPLETE/STATUS/ACK/ABORT only; none revokes ACTIVE.
 * A successful Logout route is intentionally NOT manufactured here.
 */
import {SESSION,cookie,csrf,mutationAllowed,noStore} from
  '../../../../src/auth/initial/index.ts';
import {getActive,revokeAlias,appendCookie,redirectLocal} from '../../../../src/auth/initial/index.ts';
import {productRequest} from '../../../../src/auth/initial/index.ts';
import {randomUUID} from 'node:crypto';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export async function POST(request:Request):Promise<Response>{
  const handle=cookie(request,SESSION);
  if(!handle)return new Response('Login required',{status:401,headers:noStore});
  try{
    if(!request.headers.get('content-type')?.startsWith('application/x-www-form-urlencoded'))
      return new Response('CSRF denied',{status:403,headers:noStore});
    const form=await request.formData();
    if([...form.keys()].join(',')!=='csrf'||typeof form.get('csrf')!=='string'||
       !mutationAllowed(request,String(form.get('csrf')),csrf(handle)))
      return new Response('CSRF denied',{status:403,headers:noStore});
    const active=await getActive(handle);
    if(!active)return new Response('Login required',
      {status:401,headers:noStore});
    // This demo calls real API #50 with the SAME trusted Product Session
    // (not the opaque browser handle). Never claim Logout for 401/503/unknown.
    if(process.env.AUTH_CI_DEMO_MODE!=='true')return new Response(
      'خروج هنوز به ابطال سروری متصل نشده است.',{status:503,headers:noStore});
    const operationId=randomUUID();
    const result=await productRequest('revoke',active,'',operationId);
    if(result.status!==200)return new Response('تأیید ابطال دریافت نشد؛ نتیجهٔ خروج نامعلوم است.',
      {status:503,headers:{...noStore,'Content-Type':'text/plain; charset=utf-8'}});
    let receipt:unknown;
    try{receipt=JSON.parse(result.body);}catch{return new Response(
      'رسید ابطال معتبر نیست.',{status:503,headers:noStore});}
    if(!receipt||typeof receipt!=='object'||
       (receipt as Record<string,unknown>).state!=='REVOKED_COMMITTED'||
       (receipt as Record<string,unknown>).operation_id!==operationId)
      return new Response('رسید ابطال معتبر نیست.',{status:503,headers:noStore});
    await revokeAlias(handle);
    const response=redirectLocal('/login?reason=logged_out');
    appendCookie(response,SESSION,'',0);
    return response;
  }catch{return new Response('Logout unavailable',{status:503,headers:noStore});}
}
