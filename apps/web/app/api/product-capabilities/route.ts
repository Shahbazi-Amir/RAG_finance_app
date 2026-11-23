/** Public, non-sensitive policy indicator only. Not an auth/session, health
 * proof or provider authorization. All Send mutations remain server-fenced.
 */
import {stagingRequested,stagingProfile} from '../../../src/auth/server/private-staging.ts';
import {selectRuntimeCapability} from '../../../src/ui/runtime-capability.ts';
import {noStore} from '../../../src/auth/server/initial-browser.ts';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export function GET():Response{
  const appOnly=process.env.PHASE3_APP_MODE==='APP_ONLY';
  let approvedNoDispatch=false;
  // Fail closed if the private Ops-owned profile cannot be validated.
  if(!appOnly&&stagingRequested()){
    try{approvedNoDispatch=stagingProfile().send_mode==='NO_DISPATCH_ONLY';}
    catch{approvedNoDispatch=false;}
  }
  const ciFixture=process.env.CI==='true'&&
    process.env.AUTH_CI_LOGIN_MODE==='true'&&
    process.env.AUTH_CI_PRODUCT_CHAT_MODE==='INVITED_RESULT_STUB_CI_ONLY';
  return Response.json(selectRuntimeCapability({
    appOnly,approvedNoDispatch,ciFixture
  }),{headers:{...noStore,'Content-Type':'application/json; charset=utf-8'}});
}
