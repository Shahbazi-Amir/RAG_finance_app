/**
 * Application-level bounded POST reader, aligned with apps/api/history_api.py:
 * MAX_JSON_BYTES=8192. No assertion about buffers in Next/Node/proxies.
 * Stops reading after the first overflow chunk and never sends it upstream.
 */
export const HISTORY_MAX_JSON_BYTES=8192;
export type BoundedBody =
  | {ok:true;bytes:Uint8Array}
  | {ok:false;status:413|415|422};

export async function boundedJsonBody(request:Request):Promise<BoundedBody>{
  const declared=request.headers.get('content-length');
  // Like the API, Content-Length is only an early rejection hint.
  if(declared!==null&&(!/^[0-9]+$/.test(declared)||Number(declared)>HISTORY_MAX_JSON_BYTES))
    return {ok:false,status:413};
  if(request.headers.get('content-type')?.split(';')[0].trim().toLowerCase()!=='application/json')
    return {ok:false,status:415};
  if(!request.body)return {ok:false,status:422};
  const reader=request.body.getReader();
  const chunks:Uint8Array[]=[];
  let count=0;
  try{
    while(true){
      const {done,value}=await reader.read();
      if(done)break;
      const chunk=value;
      if(count+chunk.byteLength>HISTORY_MAX_JSON_BYTES){
        // Don't collect the overflowing chunk or request any more chunks.
        void reader.cancel().catch(()=>undefined);
        return {ok:false,status:413};
      }
      count+=chunk.byteLength;
      chunks.push(chunk);
    }
  }catch{
    void reader.cancel().catch(()=>undefined);
    return {ok:false,status:422}; // aborted/truncated upload, no forwarding
  }finally{
    reader.releaseLock();
  }
  if(declared!==null&&Number(declared)!==count)return {ok:false,status:422};
  const bytes=new Uint8Array(count);
  let offset=0;
  for(const part of chunks){bytes.set(part,offset);offset+=part.byteLength;}
  return {ok:true,bytes};
}
