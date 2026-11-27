import {headers} from 'next/headers';
import {SESSION,cookie,csrf,secureBrowser} from '../../src/auth/server/initial-browser.ts';
import ProductChat from '../../src/ui/product-chat';
import './history.css';

export default async function HistoryPage(){
  const request=new Request('http://127.0.0.1',{headers:await headers()});
  const handle=cookie(request,SESSION);
  let logoutCsrf:string|undefined;
  if(handle&&secureBrowser(request)){
    try{logoutCsrf=csrf(handle);}catch{/* Auth configuration is unavailable. */}
  }
  return <ProductChat logoutCsrf={logoutCsrf}/>;
}
