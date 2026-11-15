/** Isolated CI-only fixture viewer: NEVER a staging or production route.
 * A real staging process rejects CI flags and cannot enable this page.
 * The browser never chooses this capability using query/body data.
 */
import {headers} from 'next/headers';
import {notFound} from 'next/navigation';
import ProductChat from '../../src/ui/product-chat';
import '../history/history.css';
export const dynamic='force-dynamic';
export default async function CiFixtureReview(){
  const h=await headers();
  if(process.env.CI!=='true'||process.env.GITHUB_ACTIONS!=='true'||
     process.env.AUTH_RUNTIME_PROFILE!==undefined||
     process.env.AUTH_CI_PRODUCT_CHAT_MODE!=='INVITED_RESULT_STUB_CI_ONLY'||
     h.get('host')!=='127.0.0.1:3000')notFound();
  return <ProductChat fixtureReview/>;
}
