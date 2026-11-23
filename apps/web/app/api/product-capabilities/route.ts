/** Public, non-sensitive policy indicator only. Not an auth/session, health
 * proof or provider authorization. All Send mutations remain server-fenced.
 */
import {stagingRequested,stagingProfile} from '../../../src/auth/server/private-staging.ts';
import {appOnlySendBlocked,selectRuntimeCapability} from '../../../src/ui/runtime-capability.ts';
import {noStore} from '../../../src/auth/server/initial-browser.ts';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export function GET():Response{
  const appOnly=appOnlySendBlocked(process.env.PHASE3_APP_MODE);
  let approvedNoDispatch=false;
  // Fail closed if the private Ops-owned profile cannot be validated.
  if(!appOnly&&stagingRequested()){
    try{approvedNoDispatch=stagingProfile().send_mode==='NO_DISPATCH_ONLY';}
    catch{approvedNoDispatch=false;}
  }
  // Isolated intercepted Chromium CI uses this fixture label without
  // enabling login, Send proxy, or any real provider.
  const ciFixture=process.env.CI==='true'&&
    process.env.AUTH_CI_PRODUCT_CHAT_MODE==='INVITED_RESULT_STUB_CI_ONLY';
  return Response.json(selectRuntimeCapability({
    appOnly,approvedNoDispatch,ciFixture
  }),{headers:{...noStore,'Content-Type':'application/json; charset=utf-8'}});
}
