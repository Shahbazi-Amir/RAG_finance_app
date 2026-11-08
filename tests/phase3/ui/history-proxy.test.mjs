import test from 'node:test';
import assert from 'node:assert/strict';
import {boundedJsonBody,HISTORY_MAX_JSON_BYTES} from '../../../apps/web/src/history/bounded-body.ts';
import {POST} from '../../../apps/web/app/api/history/[...path]/route.ts';

const encoder=new TextEncoder();
function streamRequest(parts,{length,contentType='application/json'}={}){
  const chunks=parts.map(p=>typeof p==='string'?encoder.encode(p):p);
  let requested=0,cancelled=false;
  const stream=new ReadableStream({
    pull(controller){
      if(requested>=chunks.length){controller.close();return;}
      controller.enqueue(chunks[requested++]);
      if(requested===chunks.length)controller.close();
    },
    cancel(){cancelled=true;}
  },{highWaterMark:0}); // no stream prefetch: assert no extra reads after overflow
  const headers={'content-type':contentType};
  if(length!==undefined)headers['content-length']=String(length);
  const request=new Request('http://127.0.0.1:3000/api/history/messages',
    {method:'POST',headers,body:stream,duplex:'half'});
  Object.defineProperty(request,'nextUrl',{value:new URL(request.url)});
  return {request,reads:()=>requested,cancelled:()=>cancelled};
}
async function scopedProxy(run){
  const oldCI=process.env.CI,oldTarget=process.env.HISTORY_UPSTREAM_ORIGIN;
  const oldFetch=globalThis.fetch;
  process.env.CI='true';process.env.HISTORY_UPSTREAM_ORIGIN='http://127.0.0.1:8111';
  let upstream=0,upstreamBody;
  globalThis.fetch=async(url,init)=>{
    upstream++;upstreamBody=init.body;
    assert.match(String(url),/^http:\/\/127\.0\.0\.1:8111\/v1\/messages$/);
    return new Response('{"accepted":true}',{status:202,
      headers:{'content-type':'application/json'}});
  };
  try{return await run({forwarded:()=>upstream,body:()=>upstreamBody});}
  finally{
    globalThis.fetch=oldFetch;
    if(oldCI===undefined)delete process.env.CI;else process.env.CI=oldCI;
    if(oldTarget===undefined)delete process.env.HISTORY_UPSTREAM_ORIGIN;
    else process.env.HISTORY_UPSTREAM_ORIGIN=oldTarget;
  }
}
const context={params:Promise.resolve({path:['messages']})};

test('boundary shares API exact 8192-byte ceiling',()=>{
  assert.equal(HISTORY_MAX_JSON_BYTES,8192);
});
test('multiple UTF-8 fragments are counted by bytes, not JS characters',async()=>{
  const payload='{"question":"'+('مالی'.repeat(120))+'"}';
  const data=encoder.encode(payload);
  const one=data.slice(0,19),two=data.slice(19,71),three=data.slice(71);
  const req=streamRequest([one,two,three],{length:data.length});
  const result=await boundedJsonBody(req.request);
  assert.equal(result.ok,true);
  assert.deepEqual(result.bytes,data);
  assert.equal(req.reads(),3);
});
test('exactly 8192 bytes are allowed; a single extra byte is rejected',async()=>{
  const full=streamRequest([encoder.encode(' '.repeat(8192))]);
  assert.equal((await boundedJsonBody(full.request)).bytes.length,8192);
  const bigger=streamRequest([encoder.encode(' '.repeat(8193))]);
  assert.deepEqual(await boundedJsonBody(bigger.request),{ok:false,status:413});
});
test('Content-Length > cap rejects before the first read or upstream call',async()=>{
  await scopedProxy(async({forwarded})=>{
    const req=streamRequest(['{}'],{length:8193});
    const res=await POST(req.request,context);
    assert.equal(res.status,413);
    assert.equal(req.reads(),0);
    assert.equal(forwarded(),0);
  });
});
test('omitted Content-Length cannot bypass limit; stop after first oversize chunk',async()=>{
  await scopedProxy(async({forwarded})=>{
    const req=streamRequest([
      encoder.encode('a'.repeat(4000)),
      encoder.encode('b'.repeat(4193)),
      encoder.encode('c'.repeat(1000))
    ]);
    const res=await POST(req.request,context);
    assert.equal(res.status,413);
    assert.equal(req.reads(),2,'third source chunk was consumed after overflow');
    assert.equal(forwarded(),0);
    assert.equal(req.cancelled(),true);
  });
});
test('understated Content-Length below cap cannot bypass actual count',async()=>{
  await scopedProxy(async({forwarded})=>{
    const req=streamRequest(['{"part":1}','{"part":2}'],{length:10});
    const res=await POST(req.request,context);
    assert.equal(res.status,422);
    assert.equal(forwarded(),0);
  });
});
test('overstated Content-Length with incomplete upload does not forward',async()=>{
  await scopedProxy(async({forwarded})=>{
    const req=streamRequest(['{"part":1}'],{length:100});
    const res=await POST(req.request,context);
    assert.equal(res.status,422);
    assert.equal(forwarded(),0);
  });
});
test('truncated JSON without a length never reaches upstream',async()=>{
  await scopedProxy(async({forwarded})=>{
    const req=streamRequest(['{"incomplete":']);
    const res=await POST(req.request,context);
    assert.equal(res.status,422);
    assert.equal(forwarded(),0);
  });
});
test('explicit stream error before completion is rejected and not forwarded',async()=>{
  const stream=new ReadableStream({
    start(controller){controller.enqueue(encoder.encode('{"part":'));controller.error(new Error('disconnect'));}
  },{highWaterMark:0});
  const req=new Request('http://127.0.0.1:3000/api/history/messages',
    {method:'POST',body:stream,duplex:'half',headers:{'content-type':'application/json'}});
  Object.defineProperty(req,'nextUrl',{value:new URL(req.url)});
  await scopedProxy(async({forwarded})=>{
    const res=await POST(req,context);assert.equal(res.status,422);assert.equal(forwarded(),0);
  });
});
test('valid bounded body forwards one exact original JSON payload',async()=>{
  await scopedProxy(async({forwarded,body})=>{
    const req=streamRequest(['{"kind":','"send_message_request"}'],{length:30});
    // No schema/DTO duplication in Proxy; the unchanged API validates payload fields.
    const res=await POST(req.request,context);
    assert.equal(res.status,422); // content-length claim intentionally mismatched
    assert.equal(forwarded(),0);
  });
  await scopedProxy(async({forwarded,body})=>{
    const payload='{"kind":"send_message_request"}';
    const req=streamRequest([payload.slice(0,9),payload.slice(9)]);
    const res=await POST(req.request,context);
    assert.equal(res.status,202);assert.equal(forwarded(),1);assert.equal(body(),payload);
  });
});
test('normal deployment remains closed before body read and upstream call',async()=>{
  const old=process.env.CI,oldTarget=process.env.HISTORY_UPSTREAM_ORIGIN;
  const oldFetch=globalThis.fetch;
  let calls=0;globalThis.fetch=async()=>{calls++;throw new Error('should not forward');};
  process.env.CI='false';process.env.HISTORY_UPSTREAM_ORIGIN='http://127.0.0.1:8111';
  try{
    const req=streamRequest(['{}']);
    const res=await POST(req.request,context);
    assert.equal(res.status,503);assert.equal(req.reads(),0);assert.equal(calls,0);
  }finally{
    globalThis.fetch=oldFetch;
    if(old===undefined)delete process.env.CI;else process.env.CI=old;
    if(oldTarget===undefined)delete process.env.HISTORY_UPSTREAM_ORIGIN;
    else process.env.HISTORY_UPSTREAM_ORIGIN=oldTarget;
  }
});
