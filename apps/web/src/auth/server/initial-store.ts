/**
 * CI-only shared local-disk server alias store. Browser handle and Product
 * session verifier are independent secrets. No production multi-host claim.
 */
import {createCipheriv,createDecipheriv,createHash,randomBytes,timingSafeEqual} from 'node:crypto';
import {open,readFile,rename,mkdir,unlink} from 'node:fs/promises';
import {join} from 'node:path';

const fail=():never=>{throw new Error('AUTH_STORE_UNAVAILABLE');};
function config():{root:string;key:Buffer}{
  if(process.env.CI!=='true'||!process.env.AUTH_CI_SHARED_STORE_DIR)fail();
  const root=process.env.AUTH_CI_SHARED_STORE_DIR??'';
  if(!root.startsWith('/tmp/')||root.includes('..'))fail();
  const key=Buffer.from(process.env.AUTH_CI_ALIAS_AES_KEY??'','base64url');
  if(key.length!==32)fail();
  return {root,key};
}
const sha=(value:string)=>createHash('sha256').update(value,'utf8').digest('hex');
const valid=(s:string)=>/^[A-Za-z0-9_-]{28,256}$/.test(s);
function isRecord(x:unknown):x is Record<string,unknown>{
  return x!==null&&typeof x==='object'&&!Array.isArray(x);
}
async function dir(){
  const c=config();await mkdir(c.root,{recursive:true,mode:0o700});return c;
}
function file(root:string,kind:'init'|'alias'|'claim'|'state',id:string){
  if(!valid(id))fail();
  return join(root,kind+'-'+sha(id)+'.json');
}
async function putNew(path:string,obj:unknown){
  const fd=await open(path,'wx',0o600);
  try{await fd.writeFile(JSON.stringify(obj));await fd.sync();}
  finally{await fd.close();}
}
async function replace(path:string,obj:unknown){
  const tmp=path+'.'+randomBytes(12).toString('hex')+'.tmp';
  const fd=await open(tmp,'wx',0o600);
  try{await fd.writeFile(JSON.stringify(obj));await fd.sync();}
  finally{await fd.close();}
  await rename(tmp,path);
}
async function read(path:string):Promise<Record<string,unknown>|null>{
  try{
    const obj:unknown=JSON.parse(await readFile(path,'utf8'));
    return isRecord(obj)?obj:null;
  }catch{return null;}
}
export const digest=sha;
export const equals=(a:string,b:string)=>{
  const aa=Buffer.from(a),bb=Buffer.from(b);
  return aa.length===bb.length&&timingSafeEqual(aa,bb);
};
export const fresh=()=>randomBytes(32).toString('base64url');
export type Init=Readonly<{attemptId:string;bffAttemptId:string;initiatorHash:string;
  stateHash:string;created:number;status:'INITIATED'}>;
export async function saveInit(v:Init){
  const c=await dir();
  const record=file(c.root,'init',v.attemptId);
  await putNew(record,v);
  try{await putNew(file(c.root,'state',v.stateHash),{attemptId:v.attemptId});}
  catch{await unlink(record).catch(()=>{});throw new Error('AUTH_STORE_UNAVAILABLE');}
}
export async function findInitForState(state:string):Promise<Init|null>{
  if(!valid(state))return null;
  const c=await dir(),record=await read(file(c.root,'state',digest(state)));
  if(typeof record?.attemptId!=='string')return null;
  const init=await readInit(record.attemptId);
  return init&&equals(init.stateHash,digest(state))?init:null;
}
export async function readInit(attempt:string):Promise<Init|null>{
  const c=await dir(),x=await read(file(c.root,'init',attempt));
  if(!x||x.status!=='INITIATED'||typeof x.created!=='number'||
      Date.now()-x.created>170000||Date.now()<x.created||
      typeof x.stateHash!=='string'||typeof x.initiatorHash!=='string'||
      typeof x.bffAttemptId!=='string')return null;
  return x as unknown as Init;
}
export async function claimInit(attempt:string):Promise<boolean>{
  const c=await dir();
  try{await putNew(file(c.root,'claim',attempt),{at:Date.now()});return true;}
  catch{return false;}
}
type Alias=Readonly<{attemptId:string;receiptId:string;ownerId:string;epoch:number;
  generation:number;ciphertext:string;iv:string;tag:string;status:'NOT_SERVE'|'ACTIVE';
  created:number}>;
export type Pending=Readonly<{attemptId:string;receiptId:string;ownerId:string;
  epoch:number;generation:number;sessionVerifier:string}>;
export async function writePending(alias:string,p:Pending):Promise<string>{
  if(!valid(alias)||!valid(p.sessionVerifier))fail();
  const c=await dir(),iv=randomBytes(12);
  const cipher=createCipheriv('aes-256-gcm',c.key,iv);
  const ciphertext=Buffer.concat([cipher.update(p.sessionVerifier,'utf8'),cipher.final()]);
  const x:Alias={attemptId:p.attemptId,receiptId:p.receiptId,ownerId:p.ownerId,
    epoch:p.epoch,generation:p.generation,ciphertext:ciphertext.toString('base64url'),
    iv:iv.toString('base64url'),tag:cipher.getAuthTag().toString('base64url'),
    status:'NOT_SERVE',created:Date.now()};
  await putNew(file(c.root,'alias',alias),x);
  return digest(alias);
}
export async function activate(alias:string,receiptId:string):Promise<boolean>{
  const c=await dir(),f=file(c.root,'alias',alias),x=await read(f);
  if(!x||x.status!=='NOT_SERVE'||x.receiptId!==receiptId)return false;
  await replace(f,{...x,status:'ACTIVE'});
  return true;
}
export async function revokeAlias(alias:string):Promise<void>{
  const c=await dir();
  try{await unlink(file(c.root,'alias',alias));}catch{}
}
export type Active=Readonly<{ownerId:string;epoch:number;generation:number;
  sessionVerifier:string;receiptId:string;attemptId:string}>;
export async function getActive(alias:string):Promise<Active|null>{
  if(!valid(alias))return null;
  const c=await dir(),x=await read(file(c.root,'alias',alias));
  if(!x||x.status!=='ACTIVE'||typeof x.created!=='number'||
      Date.now()-x.created>500000)return null;
  try{
    const dec=createDecipheriv('aes-256-gcm',c.key,
      Buffer.from(String(x.iv),'base64url'));
    dec.setAuthTag(Buffer.from(String(x.tag),'base64url'));
    const raw=Buffer.concat([dec.update(Buffer.from(String(x.ciphertext),'base64url')),dec.final()])
      .toString('utf8');
    if(!valid(raw)||typeof x.ownerId!=='string'||
      !Number.isSafeInteger(x.epoch)||!Number.isSafeInteger(x.generation))return null;
    return {ownerId:x.ownerId,epoch:Number(x.epoch),generation:Number(x.generation),
      sessionVerifier:raw,receiptId:String(x.receiptId),attemptId:String(x.attemptId)};
  }catch{return null;}
}
