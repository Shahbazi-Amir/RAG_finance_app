export function keycloakCookieExpiry():string[]{
  const path=process.env.AUTH_KEYCLOAK_REALM_COOKIE_PATH??'/realms/finance-staging/';
  if(!/^\/realms\/[A-Za-z0-9._-]{1,100}\/$/.test(path)||/\/\.{1,2}\/$/.test(path))
    throw new Error('Invalid Keycloak realm cookie path');

  // Keycloak's realm cookie path can also appear without a trailing slash.
  return [path,path.slice(0,-1)].flatMap(realmPath=>
    ['KEYCLOAK_IDENTITY','KEYCLOAK_SESSION','KEYCLOAK_IDENTITY_LEGACY','KEYCLOAK_SESSION_LEGACY']
      .map(name=>name+'=; Path='+realmPath+
        '; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; Secure'));
}
