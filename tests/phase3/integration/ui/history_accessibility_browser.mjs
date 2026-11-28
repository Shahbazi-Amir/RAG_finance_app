// Loopback-only browser coverage. Route fixtures model a read-only History API.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const base = new URL(process.env.HISTORY_BROWSER_BASE ?? 'http://127.0.0.1:3000');
assert.equal(base.hostname, '127.0.0.1');
assert.equal(base.protocol, 'http:');
const playwright = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const engine = process.env.HISTORY_BROWSER_ENGINE ?? 'chromium';
assert.ok(['chromium', 'firefox', 'webkit'].includes(engine));
const registry = JSON.parse(await readFile(new URL(
  '../../../../packages/contracts/fixtures/product.v1.cases.json', import.meta.url), 'utf8'));
const fixture = id => structuredClone(registry.cases.find(entry =>
  entry.case_id === id && entry.expected_valid).document);
const titles = ['گفت‌وگوی اول', 'گفت‌وگوی دوم'];
const ids = ['conv_browser_first', 'conv_browser_second'];
const browser = await playwright[engine].launch({
  executablePath: engine === 'chromium' ? process.env.CHROMIUM_EXECUTABLE : undefined,
});
const context = await browser.newContext({viewport: {width: 1280, height: 800}});
let availability = 'ready';
let writes = 0;
try {
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  await page.route('**/api/history/**', async route => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (req.method() !== 'GET') {
      writes++;
      await route.fulfill({status: 503});
    } else if (path.endsWith('/conversations')) {
      if (availability === 'offline') return route.fulfill({status: 503});
      if (availability === 'revoked') return route.fulfill({status: 401});
      const doc = fixture('valid_paginated_conversations');
      doc.items = ids.map((id, index) => ({...fixture('valid_conversation'),
        conversation_id: id, title: titles[index],
        created_at: `2026-01-0${2 - index}T00:00:00Z`, updated_at: '2026-01-02T00:00:00Z'}));
      Object.assign(doc.page, {limit: 2, has_more: false, next_cursor: null});
      await route.fulfill({json: doc});
    } else {
      const id = path.split('/').at(-2);
      assert.ok(ids.includes(id));
      const doc = fixture('valid_history_messages_page');
      doc.conversation_id = id;
      doc.items = [{...fixture('valid_user_message'), conversation_id: id,
        text: 'پیام ' + titles[ids.indexOf(id)] + ' ABC-123'}];
      doc.answers = [];
      Object.assign(doc.page, {limit: 30, has_more: false, next_cursor: null});
      await route.fulfill({json: doc});
    }
  });
  await page.goto(new URL('/history', base).href);
  const nav = page.getByRole('navigation', {name: 'مکالمات ثبت‌شده'});
  const log = page.getByRole('log', {name: 'پیام‌های گفت‌وگوی انتخاب‌شده'});
  const first = nav.getByRole('button', {name: titles[0]});
  const second = nav.getByRole('button', {name: titles[1]});
  await first.waitFor();
  assert.equal(await page.locator('html').getAttribute('lang'), 'fa');
  assert.equal(await page.locator('html').getAttribute('dir'), 'rtl');
  await page.keyboard.press('Tab');
  assert.equal(await page.locator('.history-skip').evaluate(el => el === document.activeElement), true);
  await page.keyboard.press('Enter');
  assert.equal(new URL(page.url()).hash, '#product-main');
  assert.equal(await page.locator('#product-main').evaluate(el => el === document.activeElement), true);
  await second.click();
  await log.getByText(/پیام گفت‌وگوی دوم/).waitFor();
  assert.equal(await second.getAttribute('aria-current'), 'page');
  assert.equal(await page.getByRole('button', {name:'ارسال پرسش'}).isDisabled(), true);
  const contrast = await second.evaluate(el => {
    const rgb = value => value.match(/[\d.]+/g).slice(0, 3).map(n => Number(n) / 255);
    const luminance = color => rgb(color).map(n => n <= 0.04045 ? n / 12.92 :
      ((n + 0.055) / 1.055) ** 2.4).reduce((sum, n, i) => sum + n * [0.2126, 0.7152, 0.0722][i], 0);
    const css = getComputedStyle(el);
    const pair = [luminance(css.color), luminance(css.backgroundColor)].sort((a,b) => a-b);
    return (pair[1] + 0.05) / (pair[0] + 0.05);
  });
  assert.ok(contrast >= 4.5, 'selected conversation contrast');
  await page.goBack();
  assert.equal(new URL(page.url()).hash, '');
  assert.equal(await second.getAttribute('aria-current'), 'page');
  console.log(engine + ' desktop: RTL, skip link, selected History after Back, disabled Send, contrast ' + contrast.toFixed(2));

  availability = 'offline';
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await page.getByTestId('history-owner-revalidation-required').waitFor();
  await log.getByText(/پیام گفت‌وگوی دوم/).waitFor({state:'hidden'});
  availability = 'ready';
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await log.getByText(/پیام گفت‌وگوی دوم/).waitFor();
  assert.equal(await second.getAttribute('aria-current'), 'page');
  assert.equal(await page.locator('.history-error[role=alert]').count(), 0, 'clear the failed History refresh alert after recovery');
  console.log(engine + ' History: outage hides messages and GET-only recovery retains selection');

  await page.setViewportSize({width:390,height:844});
  const trigger = page.getByRole('button', {name:'بازکردن فهرست گفت‌وگوها'});
  await trigger.click();
  const drawer = page.getByRole('dialog', {name:'فهرست گفتگوها'});
  const close = drawer.getByRole('button', {name:'بستن فهرست'});
  await close.waitFor();
  assert.equal(await drawer.getAttribute('aria-modal'), 'true');
  assert.equal(await close.evaluate(el => el === document.activeElement), true);
  assert.equal(await page.locator('.history-main').evaluate(el => el.inert), true);
  await page.keyboard.press('Shift+Tab');
  assert.equal(await drawer.getByRole('link').evaluate(el => el === document.activeElement), true);
  await page.keyboard.press('Tab');
  assert.equal(await close.evaluate(el => el === document.activeElement), true);
  assert.ok(await close.evaluate(el => {
    const style = getComputedStyle(el);
    return style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) >= 2;
  }), 'visible keyboard focus');
  await page.keyboard.press('Escape');
  await drawer.waitFor({state:'hidden'});
  assert.equal(await trigger.evaluate(el => el === document.activeElement), true);
  assert.equal(await trigger.getAttribute('aria-expanded'), 'false');
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
  console.log(engine + ' mobile: modal semantics, focus trap, Escape and focus restoration, no overflow');

  availability = 'revoked';
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await page.getByTestId('history-login-required').waitFor();
  assert.equal(await log.getByText(/پیام گفت‌وگوی دوم/).count(), 0);
  assert.equal(writes, 0);
  console.log(engine + ' revoked: History purged after 401, zero writes');
} finally {
  await context.close();
  await browser.close();
}
