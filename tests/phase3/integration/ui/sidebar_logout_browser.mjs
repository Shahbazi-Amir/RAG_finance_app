// Local Playwright smoke for the built Web app and a synthetic Product peer.
import assert from 'node:assert/strict';
import {execFileSync, spawn} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import {createServer as httpServer, request} from 'node:http';
import {createServer as httpsServer} from 'node:https';
import {once} from 'node:events';
import {fileURLToPath} from 'node:url';
import {activate, getActive, writePending} from '../../../../apps/web/src/auth/server/initial-store.ts';
import {freshCookie, SESSION} from '../../../../apps/web/src/auth/server/initial-browser.ts';

const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = new URL('../../../../', import.meta.url);
const scratch = await mkdtemp('/tmp/rag-sidebar-logout-');
const servers = [];
let next, browser;
async function listen(server) {
  servers.push(server);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return server.address().port;
}
try {
  const keyPath = scratch + '/tls.key';
  const certPath = scratch + '/tls.pem';
  const opensslConfig = scratch + '/openssl.cnf';
  await writeFile(opensslConfig,
    '[req]\ndistinguished_name=dn\n[dn]\n[extensions]\nsubjectAltName=IP:127.0.0.1\n');
  execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes',
    '-config', opensslConfig, '-subj', '/CN=127.0.0.1', '-extensions', 'extensions',
    '-days', '1', '-keyout', keyPath, '-out', certPath], {stdio:'ignore'});
  const [key, cert] = await Promise.all([readFile(keyPath), readFile(certPath)]);
  let revokeCalls = 0;
  const privatePort = await listen(httpsServer({key, cert, ca:cert,
    requestCert:true, rejectUnauthorized:true}, async (req, res) => {
    if (req.method !== 'POST' || req.url !== '/internal/auth/session/v1/revoke-one') {
      res.writeHead(503).end();
      return;
    }
    revokeCalls++;
    let body = '';
    for await (const chunk of req) body += chunk;
    const {operation_id} = JSON.parse(body);
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({state:'REVOKED_COMMITTED', operation_id}));
  }));
  const proof = freshCookie();
  const reservation = httpServer();
  const nextPort = await listen(reservation);
  await new Promise(resolve => reservation.close(resolve));
  const proxyPort = await listen(httpsServer({key, cert}, (req, res) => {
    const upstream = request({host:'127.0.0.1', port:nextPort, method:req.method,
      path:req.url, headers:{...req.headers, 'x-auth-ci-proxy-proof':proof}}, reply => {
      res.writeHead(reply.statusCode, reply.headers);
      reply.pipe(res);
    });
    upstream.on('error', () => res.writeHead(503).end());
    req.pipe(upstream);
  }));
  const origin = 'https://127.0.0.1:' + proxyPort;
  Object.assign(process.env, {
    CI:'true', AUTH_CI_DEMO_MODE:'true', AUTH_CI_PUBLIC_ORIGIN:origin,
    AUTH_CI_CSRF_SECRET:freshCookie(), AUTH_CI_PROXY_SECRET:proof,
    AUTH_CI_SHARED_STORE_DIR:scratch, AUTH_CI_ALIAS_AES_KEY:freshCookie(),
    AUTH_CI_IDP_AUTHORIZATION_ORIGIN:'http://127.0.0.1:9',
    AUTH_CI_PRODUCT_ORIGIN:'https://127.0.0.1:' + privatePort,
    AUTH_CI_PRODUCT_ISSUER:'urn:fixture:web', AUTH_CI_PRODUCT_AUDIENCE:'urn:fixture:product',
    AUTH_CI_PRODUCT_KID:'fixture', AUTH_CI_PRODUCT_SIGN_KEY:keyPath,
    AUTH_CI_BOOTSTRAP_CA:certPath, AUTH_CI_BOOTSTRAP_CERT:certPath, AUTH_CI_BOOTSTRAP_KEY:keyPath,
  });
  next = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start',
    '-H', '127.0.0.1', '-p', String(nextPort)], {
    cwd:fileURLToPath(new URL('apps/web/', root)), stdio:'ignore',
  });
  for (let attempt = 0; ; attempt++) {
    try {
      if ((await fetch('http://127.0.0.1:' + nextPort)).ok) break;
    } catch { /* Wait for isolated Next process. */ }
    if (attempt === 60 || next.exitCode !== null) throw new Error('Next did not start');
    await new Promise(resolve => setTimeout(resolve, 200));
  }

  browser = await chromium.launch({
    executablePath:process.env.CHROMIUM_EXECUTABLE, headless:true,
  });
  for (const mobile of [false, true]) {
    const handle = freshCookie();
    const receiptId = randomUUID();
    await writePending(handle, {attemptId:randomUUID(), receiptId, ownerId:'fixture-owner',
      epoch:0, generation:0, sessionVerifier:freshCookie()});
    assert.equal(await activate(handle, receiptId), true);
    const context = await browser.newContext({ignoreHTTPSErrors:true,
      viewport:mobile ? {width:390,height:844} : {width:1280,height:800}});
    const realm = '/realms/finance-staging/';
    const realmCookies = ['KEYCLOAK_IDENTITY', 'KEYCLOAK_SESSION'];
    await context.addCookies([{name:SESSION,value:handle,url:origin,secure:true,httpOnly:true},
      ...realmCookies.map(name => ({name,value:'fixture',domain:'127.0.0.1',
        path:realm,secure:true,httpOnly:true}))]);
    const page = await context.newPage();
    await page.goto(origin + (mobile ? '/history' : '/'));
    if (mobile) await page.getByRole('button', {name:'بازکردن فهرست گفت‌وگوها'}).click();
    const submit = page.getByTestId('sidebar-logout');
    await submit.waitFor();
    assert.equal((await context.request.get(origin + '/api/auth/logout')).status(), 405);
    const blocked = await page.evaluate(async () => (await fetch('/api/auth/logout', {
      method:'POST', credentials:'same-origin', body:new URLSearchParams({csrf:'invalid'}),
    })).status);
    assert.equal(blocked, 403);
    assert.equal(revokeCalls, mobile ? 1 : 0);
    assert.ok(await getActive(handle));
    const [receipt] = await Promise.all([
      page.waitForResponse(res => res.url() === origin + '/api/auth/logout' &&
        res.request().method() === 'POST'),
      submit.click(),
    ]);
    assert.equal(receipt.status(), 303);
    for (const name of realmCookies) {
      assert.ok((await receipt.headerValues('set-cookie')).some(value =>
        value.startsWith(name + '=;') && value.includes('Path=' + realm + ';') &&
        value.includes('Max-Age=0')));
    }
    await page.getByTestId('logout-success').waitFor();
    await page.getByTestId('login-submit').waitFor();
    assert.equal(new URL(page.url()).pathname, '/login');
    assert.equal(await getActive(handle), null);
    const cookies = await context.cookies(origin + realm);
    assert.ok(cookies.every(cookie => cookie.name !== SESSION && !realmCookies.includes(cookie.name)));
    await context.close();
    console.log((mobile ? 'mobile /history' : 'desktop /') + ': CSRF 403, logout POST 303, cookies removed');
  }
  assert.equal(revokeCalls, 2);

  const page = await browser.newPage({viewport:{width:390,height:844}});
  const css = await readFile(new URL('infra/arvan-staging/themes/moshaver-mali/login/resources/css/moshaver.css', root), 'utf8');
  await page.setContent(`<style>
    .pf-v5-c-login__main-header{border-top:4px solid blue}
    ${css}</style><main class="pf-v5-c-login__main">
    <header class="pf-v5-c-login__main-header"><b>ورود</b><span class="mm-badge"></span></header>
    <span class="pf-v5-c-form-control__utilities">!</span>
    <span class="kc-feedback-text">رمز عبور اشتباه است</span></main>`);
  assert.equal(await page.locator('header').evaluate(el => getComputedStyle(el).borderTopWidth), '0px');
  assert.equal(await page.locator('.mm-badge').evaluate(el => getComputedStyle(el).direction), 'ltr');
  assert.match(await page.locator('.mm-badge').evaluate(el => getComputedStyle(el).backgroundSize),
    /^3px 6px, 3px 10px, 3px 15px/);
  assert.equal(await page.locator('.pf-v5-c-form-control__utilities').isVisible(), false);
  assert.equal(await page.locator('.kc-feedback-text').isVisible(), true);
  console.log('mobile theme CSS: inherited border removed, ascending bars, error text visible');
} finally {
  await browser?.close();
  if (next?.exitCode === null) next.kill();
  for (const server of servers) {
    if (server.listening) {
      server.closeAllConnections();
      await new Promise(resolve => server.close(resolve));
    }
  }
  await rm(scratch, {recursive:true, force:true});
}
