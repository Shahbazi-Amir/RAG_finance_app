/** Server-side Ops profile. No CI emulation, no browser-supplied settings.
 * A secret 0600 config file must be installed by the authorized operator.
 * The Product API independently requires startup admission for dispatch.
 */
import {lstatSync,readFileSync} from 'node:fs';
import {isAbsolute} from 'node:path';

const denied=():never=>{throw new Error('PRIVATE_STAGING_DENIED');};
const fields=[
 'public_origin','idp_authorization_origin','bootstrap_origin','product_origin',
 'store_dir','proxy_proof_file','csrf_secret_file','alias_key_file',
 'bootstrap_sign_key_file','product_sign_key_file','tls_ca_file',
 'tls_client_cert_file','tls_client_key_file','bootstrap_issuer',
 'bootstrap_audience','bootstrap_kid','product_issuer','product_audience',
 'product_kid','send_mode'
] as const;
type Field=typeof fields[number];
type SessionLifetime=Readonly<{idle_seconds:number;absolute_seconds:number}>;
export type PrivateStaging=Readonly<Record<Field,string>&{session_lifetime?:SessionLifetime}>;
export const stagingRequested=()=>process.env.AUTH_RUNTIME_PROFILE==='private-staging';
function owned(path:string,kind:'file'|'dir'):void{
 if(!isAbsolute(path)||path.includes('/../')||path.endsWith('/..'))denied();
 try{
  const s=lstatSync(path);
  if(s.isSymbolicLink()||
     (kind==='file'?(!s.isFile()||s.size<1||s.size>65536):!s.isDirectory())||
     (s.mode&0o077)!==0||(s.uid!==process.getuid?.()&&s.uid!==0))denied();
 }catch{return denied();}
}
export function stagingSecret(path:string):string{
 owned(path,'file');
 try{return readFileSync(path,'utf8');}catch{return denied();}
}
const originOk=(value:string):boolean=>{
 try{
  const u=new URL(value);
  return u.protocol==='https:'&&!!u.hostname&&u.origin===value&&
    u.pathname==='/'&&!u.search&&!u.hash&&!u.username&&!u.password;
 }catch{return false;}
};
export function stagingProfile():PrivateStaging{
 if(!stagingRequested()||process.env.CI==='true'||process.env.GITHUB_ACTIONS==='true'||
    process.env.AUTH_CI_LOGIN_MODE!==undefined||
    process.env.AUTH_CI_DEMO_MODE!==undefined||
    process.env.AUTH_CI_PRODUCT_CHAT_MODE!==undefined)denied();
 const raw=stagingSecret(process.env.AUTH_STAGING_CONFIG_FILE??'');
 let parsed:unknown;
 try{parsed=JSON.parse(raw);}catch{return denied();}
 if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))denied();
 const x=parsed as Record<string,unknown>;
 if(Object.keys(x).some(k=>k!=='session_lifetime'&&!fields.includes(k as Field))||
    fields.some(k=>typeof x[k]!=='string'||!x[k]))denied();
 const lifetime=x.session_lifetime;
 if(Object.hasOwn(x,'session_lifetime')){
   if(!lifetime||typeof lifetime!=='object'||Array.isArray(lifetime))return denied();
   const {idle_seconds:idle,absolute_seconds:absolute}=lifetime as SessionLifetime;
   if(Object.keys(lifetime).length!==2||!Number.isInteger(idle)||!Number.isInteger(absolute)||
      idle<3600||absolute<idle||absolute>28800)return denied();
 }
 const p=x as unknown as PrivateStaging;
 if(p.public_origin!=='https://ragfinance.ir'||
    !originOk(p.public_origin)||!originOk(p.idp_authorization_origin)||
    !originOk(p.bootstrap_origin)||!originOk(p.product_origin)||
    ['bootstrap_origin','product_origin'].some(k=>
      new URL(p[k as Field]).hostname==='ragfinance.ir')||
    !['DISABLED','NO_DISPATCH_ONLY','LIVE_DISPATCH'].includes(p.send_mode)||
    ![p.bootstrap_issuer,p.bootstrap_audience,p.product_issuer,p.product_audience]
      .every(v=>v.startsWith('urn:')&&v.length<=180)||
    ![p.bootstrap_kid,p.product_kid].every(v=>
      /^[A-Za-z0-9_.-]{1,80}$/.test(v)))denied();
 owned(p.store_dir,'dir');
 for(const k of fields.filter(k=>k.endsWith('_file')))stagingSecret(p[k]);
 if(!/^[A-Za-z0-9_-]{43}$/.test(stagingSecret(p.alias_key_file).trim())||
    Buffer.from(stagingSecret(p.alias_key_file).trim(),'base64url').length!==32||
    stagingSecret(p.csrf_secret_file).trim().length<32||
    stagingSecret(p.proxy_proof_file).trim().length<32)denied();
 return p;
}

export const stagingSendEnabled=()=>['NO_DISPATCH_ONLY','LIVE_DISPATCH'].includes(stagingProfile().send_mode);

export function stagingSessionLifetime():SessionLifetime|undefined{
 return stagingRequested()?stagingProfile().session_lifetime:undefined;
}
