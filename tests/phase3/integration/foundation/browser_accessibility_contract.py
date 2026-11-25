"""UI-11 bounded real-browser accessibility checks.
Accessible role/name/description assertions are not an actual screen-reader
audio evaluation or a full WCAG conformance statement. No network mocking.
"""
from playwright.async_api import expect

# Explicit engineering thresholds for these checks only, not target approval.
CONTRAST = r"""(el, part) => {
  const rgb = v => {
    if (!/^rgba?\(/.test(v)) throw Error('UNSUPPORTED_COMPUTED_COLOR');
    const a=v.match(/[0-9.]+/g).map(Number);
    if(a.length===3)a.push(1);
    if(a.length!==4 || a.some(x=>!Number.isFinite(x)) ||
       a.slice(0,3).some(x=>x<0||x>255) || a[3]<0||a[3]>1)
      throw Error('INVALID_COLOR');
    return a;
  };
  const luminance = c => c.slice(0,3).map(x=>x/255)
    .map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4)
    .reduce((a,x,i)=>a+x*[.2126,.7152,.0722][i],0);
  const st=getComputedStyle(el);
  const fg=rgb(part==='focus'?st.outlineColor:st.color);
  if(fg[3]!==1)throw Error('NON_OPAQUE_FOREGROUND');
  if(part==='focus'&& (st.outlineStyle==='none'||parseFloat(st.outlineWidth)<2))
    throw Error('MISSING_FOCUS_INDICATOR');
  let bg=null;
  for(let n=part==='focus'?el.parentElement:el;n;n=n.parentElement){
    const ns=getComputedStyle(n),c=rgb(ns.backgroundColor);
    if(ns.backgroundImage!=='none')throw Error('UNSUPPORTED_BACKGROUND_IMAGE');
    if(c[3]===1){bg=c;break;}
    if(c[3]!==0)throw Error('UNSUPPORTED_ALPHA_BACKGROUND');
  }
  if(!bg)throw Error('NO_OPAQUE_BACKGROUND');
  const a=luminance(fg),b=luminance(bg);
  return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
}"""


async def contrast(locator,label,*,part="text"):
    await expect(locator).to_be_visible()
    value=await locator.evaluate(CONTRAST,part)
    assert value >= (3 if part=="focus" else 4.5),("UI11_CONTRAST",label,round(value,2))
    return round(value,2)


async def assert_history_accessibility(page):
    assert await page.locator("html").get_attribute("lang")=="fa"
    assert await page.locator("html").get_attribute("dir")=="rtl"
    await expect(page.get_by_role("main")).to_have_count(1)
    await expect(page.get_by_role("heading",level=1,name="گفت‌وگوی مالی")).to_have_count(1)
    await expect(page.get_by_role("navigation",name="مکالمات ثبت‌شده")).to_be_visible()
    await expect(page.get_by_role("log",name="پیام‌های گفت‌وگوی انتخاب‌شده")).to_be_visible()
    for role,name in (("textbox","پرسش فارسی"),("button","ارسال پرسش"),("button","گفت‌وگوی تازه")):
        control=page.get_by_role(role,name=name,exact=True)
        await expect(control).to_be_disabled()
        await expect(control).to_have_accessible_description(
            "برنامه در حالت بدون موتور فعال است؛ تاریخچه قابل مشاهده است، اما ارسال پرسش و تولید پاسخ غیرفعال است.")
    empty=page.locator(".history-empty")
    if await empty.count():
        await expect(empty).to_contain_text("ارسال پرسش غیرفعال است")
    labels=[
        (page.get_by_test_id("app-runtime-capability"),"capability"),
        (page.get_by_test_id("educational-boundary"),"education"),
        (page.get_by_role("link",name="حساب، حریم خصوصی و وضعیت قابلیت‌ها"),"account-link"),
        (page.get_by_role("button",name="بازخوانی",exact=True),"refresh"),
        (page.locator(".history-thread-detail").first,"thread-id"),
    ]
    result={}
    for el,name in labels:result[name]=await contrast(el,name)
    # The earlier skip-link test established actual keyboard focus on heading.
    # Check a visible interactive control using keyboard modality too.
    refresh=page.get_by_role("button",name="بازخوانی",exact=True)
    await refresh.focus()
    await page.keyboard.press("Shift+Tab")
    await page.keyboard.press("Tab")
    await expect(refresh).to_be_focused()
    result["refresh-focus"]=await contrast(refresh,"refresh-focus",part="focus")
    print("F3_UI11_HISTORY_ACCESSIBLE_ROLE_DESCRIPTION_CONTRAST_PASS",result,flush=True)


async def assert_account_accessibility(page):
    await expect(page.get_by_role("main")).to_have_count(1)
    await expect(page.get_by_role("heading",level=1,name="حساب و حریم خصوصی")).to_have_count(1)
    await expect(page.get_by_role("navigation",name="مسیرهای حساب")).to_be_visible()
    for name in ("رضایت و حریم خصوصی","درخواست حذف داده و حساب","خروجی داده و بازخورد"):
        section=page.get_by_role("region",name=name,exact=True)
        await expect(section).to_be_visible()
        await expect(section.get_by_role("heading",level=2,name=name)).to_be_visible()
        status=section.get_by_role("status")
        await expect(status).to_be_visible()
        await contrast(status,"account-policy-status")
    link=page.get_by_role("link",name="بازگشت به گفت‌وگو")
    await contrast(link,"return-link")
    # Two links only; no consent/delete/export/feedback form or toggle.
    await expect(page.get_by_role("main").get_by_role("button")).to_have_count(0)
    await expect(page.get_by_role("main").get_by_role("checkbox")).to_have_count(0)
    await expect(page.get_by_role("main").get_by_role("switch")).to_have_count(0)
    await expect(page.get_by_role("main").get_by_role("link")).to_have_count(2)
    await link.focus()
    await page.keyboard.press("Shift+Tab")
    await page.keyboard.press("Tab")
    await expect(link).to_be_focused()
    await contrast(link,"return-link-focus",part="focus")
    print("F3_UI11_ACCOUNT_ACCESSIBLE_REGIONS_AND_NO_MUTATION_CONTROLS_PASS",flush=True)
