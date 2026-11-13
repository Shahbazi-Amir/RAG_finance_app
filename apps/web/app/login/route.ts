import {cookie,csrf,freshCookie,INIT,SESSION,secureBrowser,appendCookie,noStore,
  publicOrigin} from '../../src/auth/server/initial-browser.ts';
import {getActive} from '../../src/auth/server/initial-store.ts';
export const dynamic='force-dynamic';
export const runtime='nodejs';
function html(content:string){
  return '<!doctype html><html lang="fa" dir="rtl"><head>'+
    '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<title>ورود | راگ مالی</title></head><body style="font-family:system-ui;padding:2rem">'+
    '<main><h1>ورود به تاریخچه</h1>'+content+'</main></body></html>';
}
export async function GET(request:Request):Promise<Response>{
  if(!secureBrowser(request))return new Response('Unavailable',{status:503,headers:noStore});
  try{
    const current=cookie(request,SESSION);
    const active=current?await getActive(current):null;
    if(active){
      const content=html('<p>نشست آزمایشی فعال است.</p>'+
        '<form method="post" action="/api/auth/logout">'+
        '<input type="hidden" name="csrf" value="'+csrf(current!)+'">'+
        '<button type="submit">خروج</button></form><a href="/history">تاریخچه</a>');
      return new Response(content,{headers:{...noStore,'Content-Type':'text/html; charset=utf-8',
        'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'"}});
    }
    const init=freshCookie();
    const text=html('<p>فقط محیط آزمون ایزوله؛ ورود تولیدی فعال نیست.</p>'+
      '<form method="post" action="/api/auth/login">'+
      '<input type="hidden" name="csrf" value="'+csrf(init)+'">'+
      '<button type="submit" data-testid="login-submit">ورود</button></form>');
    const response=new Response(text,{headers:{...noStore,'Content-Type':'text/html; charset=utf-8',
      'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'"}});
    appendCookie(response,INIT,init,180);
    return response;
  }catch{
    return new Response('Unavailable',{status:503,headers:noStore});
  }
}
