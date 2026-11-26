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
  let mode: string|undefined;
  // Fail closed if the private Ops-owned profile cannot be validated.
  if(!appOnly&&stagingRequested()){
    try{mode=stagingProfile().send_mode;}
    catch{mode=undefined;}
  }
  // Fixture authorization belongs exclusively to Playwright interception,
  // not to any running Next server, even on CI.
  return Response.json(selectRuntimeCapability({
    appOnly,approvedNoDispatch:mode==='NO_DISPATCH_ONLY',
    approvedLive:mode==='LIVE_DISPATCH',ciFixture:false
  }),{headers:{...noStore,'Content-Type':'application/json; charset=utf-8'}});
}
