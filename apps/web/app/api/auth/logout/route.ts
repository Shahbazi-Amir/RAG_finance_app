/**
 * Explicit fail-closed Logout boundary.
 * API #48 exposes START/COMPLETE/STATUS/ACK/ABORT only; none revokes ACTIVE.
 * A successful Logout route is intentionally NOT manufactured here.
 */
import {SESSION,cookie,csrf,mutationAllowed,noStore} from
  '../../../../src/auth/initial/index.ts';
import {getActive} from '../../../../src/auth/initial/index.ts';
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
    if(!await getActive(handle))return new Response('Login required',
      {status:401,headers:noStore});
    // No API-controlled ACTIVE revoke_one commit receipt exists in pinned #48.
    // Do NOT clear Cookie and claim logout; no alias-only revocation proof.
    return new Response('خروج تأیید نشد؛ ابطال نشست در API آماده نیست.',
      {status:503,headers:{...noStore,'Content-Type':'text/plain; charset=utf-8'}});
  }catch{return new Response('Logout unavailable',{status:503,headers:noStore});}
}
