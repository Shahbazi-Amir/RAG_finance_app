import {cookie,csrf,freshCookie,INIT,SESSION,secureBrowser,appendCookie,noStore,
  publicOrigin} from '../../src/auth/initial/index.ts';
import {getActive} from '../../src/auth/initial/index.ts';
export const dynamic='force-dynamic';
export const runtime='nodejs';
function html(content:string){
  return '<!doctype html><html lang="fa" dir="rtl"><head>'+
    '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<title>ورود امن | راگ مالی</title><style>'+
    ':root{color-scheme:light}*{box-sizing:border-box}body{margin:0;min-height:100vh;'+
    'background:linear-gradient(125deg,#eff6ff,#f8fafc 58%,#ecfdf5);color:#14243b;'+
    'font-family:Tahoma,system-ui,sans-serif;display:grid;place-items:center;padding:24px}'+
    'main{width:min(100%,470px);padding:clamp(24px,5vw,44px);border-radius:22px;'+
    'background:white;box-shadow:0 18px 60px #0a30571c;border:1px solid #dbe6f5}'+
    '.brand{font-weight:800;color:#155e75;letter-spacing:.3px}h1{font-size:clamp(24px,5vw,30px);'+
    'line-height:1.5;margin:18px 0 8px}p{line-height:1.9;color:#475569}'+
    '.label{padding:12px 16px;background:#f1f5f9;border-radius:12px;font-size:14px}'+
    'button{border:0;border-radius:13px;background:#0e7490;color:white;cursor:pointer;'+
    'padding:14px 26px;font:700 16px Tahoma,system-ui;width:100%;margin-top:20px}'+
    'button:hover{background:#155e75}button:focus-visible,a:focus-visible{outline:3px solid #fb923c}'+
    'a{color:#0369a1}small{display:block;margin-top:20px;color:#64748b;line-height:1.8}'+
    '.success{color:#166534;background:#ecfdf5;border:1px solid #bbf7d0;'+
    'border-radius:12px;padding:12px}.error{color:#991b1b;background:#fef2f2;'+
    'border-radius:12px;padding:12px}</style></head><body>'+
    '<main><div class="brand">◈ راگ مالی | فاز سوم</div>'+content+
    '<small>این یک محیط آزمایشی ایزوله با داده‌ها و حساب‌های مصنوعی است؛ اتصال موتور زنده ندارد.</small>'+
    '</main></body></html>';
}
export async function GET(request:Request):Promise<Response>{
  if(!secureBrowser(request))return new Response('Unavailable',{status:503,headers:noStore});
  try{
    const current=cookie(request,SESSION);
    const active=current?await getActive(current):null;
    if(active){
      const label=active.ownerId===process.env.AUTH_CI_DEMO_OWNER_A?'حساب نمایشی الف'
        :active.ownerId===process.env.AUTH_CI_DEMO_OWNER_B?'حساب نمایشی ب'
        :'نشست آزمایشی معتبر';
      const content=html('<h1>مدیریت نشست</h1><p class="label">'+label+
        ' — نشست فعال است</p><p><a href="/history">بازگشت به تاریخچهٔ خصوصی</a></p>'+
        '<form method="post" action="/api/auth/logout">'+
        '<input type="hidden" name="csrf" value="'+csrf(current!)+'">'+
        '<button type="submit" data-testid="logout-submit">خروج امن از حساب</button></form>');
      return new Response(content,{headers:{...noStore,'Referrer-Policy':'same-origin','Content-Type':'text/html; charset=utf-8',
        'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'"}});
    }
    const init=freshCookie();
    // A native same-origin form POST obtains a 303 to this precise IdP.
    // CSP form-action also checks the redirect target, not only POST /api/auth/login.
    // Allow ONLY the statically provisioned loopback Keycloak origin in this
    // isolated CI demo; never accept a query/body-selected origin.
    const idpOrigin=process.env.AUTH_CI_IDP_AUTHORIZATION_ORIGIN??'';
    const match=/^http:\/\/127\.0\.0\.1:([0-9]{1,5})$/.exec(idpOrigin);
    const port=match?Number(match[1]):0;
    if(!match||port<1||port>65535)throw new Error('CI_PINNED_IDP_REQUIRED');
    const formPolicy="default-src 'none'; style-src 'unsafe-inline'; form-action 'self' "+idpOrigin+"; base-uri 'none'";
    const reason=new URL(request.url).searchParams.get('reason');
    const result=reason==='logged_out'
      ?'<p class="success" data-testid="logout-success">خروج با ابطال تأییدشدهٔ نشست انجام شد.</p>'
      :reason==='auth_failed'
      ?'<p class="error" data-testid="login-error">درخواست ورود معتبر نبود؛ دوباره تلاش کنید.</p>':'';
    const text=html('<h1>ورود به تاریخچهٔ مالی</h1>'+result+
      '<p>با یکی از حساب‌های مصنوعی «نمایشی الف» یا «نمایشی ب» وارد شوید؛ هر حساب فقط تاریخچهٔ خودش را می‌بیند.</p>'+
      '<p class="label">تاریخچهٔ نمونهٔ سپهر و دماوند؛ اطلاعات غیرواقعی.</p>'+
      '<form method="post" action="/api/auth/login">'+
      '<input type="hidden" name="csrf" value="'+csrf(init)+'">'+
      '<button type="submit" data-testid="login-submit">ورود</button></form>');
    const response=new Response(text,{headers:{...noStore,'Referrer-Policy':'same-origin','Content-Type':'text/html; charset=utf-8',
      'Content-Security-Policy':formPolicy}});
    appendCookie(response,INIT,init,180);
    return response;
  }catch{
    return new Response('Unavailable',{status:503,headers:noStore});
  }
}
