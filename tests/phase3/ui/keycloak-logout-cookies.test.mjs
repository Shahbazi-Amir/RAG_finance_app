import assert from 'node:assert/strict';
import test from 'node:test';
import {keycloakCookieExpiry} from '../../../apps/web/app/api/auth/logout/keycloak-cookies.ts';

test('logout expires Keycloak cookies for both spellings of the exact realm path', () => {
  assert.deepEqual(keycloakCookieExpiry(), [
    '/realms/finance-staging/',
    '/realms/finance-staging',
  ].flatMap(path => [
    'KEYCLOAK_IDENTITY', 'KEYCLOAK_SESSION', 'KEYCLOAK_IDENTITY_LEGACY', 'KEYCLOAK_SESSION_LEGACY',
  ].map(name => name + '=; Path=' + path +
    '; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; Secure')));
});

test('logout accepts a configured realm path and rejects attribute injection', () => {
  try {
    process.env.AUTH_KEYCLOAK_REALM_COOKIE_PATH = '/realms/alternate/';
    assert.ok(keycloakCookieExpiry().every(value => value.includes('Path=/realms/alternate')));
    for (const path of ['/realms/main/; Domain=example.invalid', '/realms/../', '/']) {
      process.env.AUTH_KEYCLOAK_REALM_COOKIE_PATH = path;
      assert.throws(keycloakCookieExpiry, /Invalid Keycloak realm cookie path/);
    }
  } finally {
    delete process.env.AUTH_KEYCLOAK_REALM_COOKIE_PATH;
  }
});
