import ProductChat from '../../src/ui/product-chat';
import {stagingRequested,stagingProfile} from '../../src/auth/server/private-staging';
import './history.css';
export default function HistoryPage(){
  // Server-authored capability, never a browser-selected query or fixture.
  const appOnly=stagingRequested()&&stagingProfile().send_mode==='DISABLED';
  return <ProductChat appOnly={appOnly}/>;
}
