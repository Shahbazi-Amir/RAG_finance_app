/**
 * Actual HTTPS with verified server CA/hostname and client mTLS. Node signer
 * is independent of the accepted Python verifier + PostgreSQL durable replay.
 * Only ephemeral runner files; never print tokens, keys or session references.
 */
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {request as httpsRequest,createServer as createHttpsServer} from 'node:https';
import {createServer as createTcpServer} from 'node:net';
import {performance} from 'node:perf_hooks';
import {randomBytes} from 'node:crypto';
import {createServiceSender,signForTrustedAttempt} from '../../../../apps/web/src/auth/server/service-sender.ts';

if(process.env.CI!=='true'||process.env.GITHUB_ACTIONS!=='true')throw Error('CI_ONLY');
const folder=process.env.BFF_TLS_DIR;
if(!folder||!folder.startsWith(process.env.RUNNER_TEMP+'/'))throw Error('CI_ONLY');
const load=name=>readFileSync(folder+'/'+name,'utf8');
const fixture=JSON.parse(readFileSync(process.env.BFF_TRUST_SESSION_FILE,'utf8'));
const target='https://127.0.0.1:8443';
const c={
  issuer:'urn:rag-finance:synthetic-bff',audience:'urn:rag-finance:api:internal-ci',
  kid:'ci-rsa-1',privateKeyPem:load('signer.key'),
  upstreamOrigin:target,allowedOrigins:[target],caPem:load('ca.crt'),
  clientCertPem:load('client.crt'),clientKeyPem:load('client.key'),timeoutMs:3000,
};
const marker=()=>('bff_'+randomBytes(12).toString('hex'));
const make=(id,{method='POST',path='/fixture',query='x=%2f&y=1',body}={})=>({
  method,rawPath:Buffer.from(path,'ascii'),rawQuery:Buffer.from(query,'ascii'),
  body:body??Buffer.from(JSON.stringify({marker:id,idempotency_key:'original-operation',question:'سؤال مالی'})),
});
const count=id=>Number(execFileSync('python',['tests/phase3/integration/ui/audit_bff_trust.py','count',id],
  {encoding:'utf8'}).trim());
const safe=async(cnf,session,op)=>createServiceSender(cnf,async()=>session)(op);
function raw(token,op,credentials=true,conf=c){
  return new Promise(resolve=>{
    let done=false;
    const finish=n=>{if(!done){done=true;resolve(n);}};
    const req=httpsRequest({
      hostname:'127.0.0.1',port:8443,path:op.rawPath.toString('latin1')+
        (op.rawQuery.length?'?'+op.rawQuery.toString('latin1'):''),
      method:op.method,ca:conf.caPem,
      ...(credentials?{cert:conf.clientCertPem,key:conf.clientKeyPem}:{}),
      rejectUnauthorized:true,agent:false,
      headers:{Authorization:'BFF-Assertion '+token,
        'Content-Type':'application/json','Content-Length':String(op.body.length)},
    },res=>{res.resume();res.on('end',()=>finish(res.statusCode));});
    req.on('error',()=>finish(-1));req.setTimeout(3000,()=>req.destroy());
    req.end(op.body);
  });
}
let checks=0;
async function check(label,callback){
  await callback();checks++;console.log('BFF_TLS_'+String(checks).padStart(2,'0')+' PASS '+label);
}
await check('verified real HTTPS mTLS, independent Python RSA, fenced PG write',async()=>{
  const id=marker(),op=make(id);
  assert.deepEqual(await safe(c,fixture.active,op),{ok:true,code:'OK'});
  assert.equal(count(id),1);
});
await check('same compact JWT durable replay rejected, no second SQL',async()=>{
  const id=marker(),op=make(id),token=signForTrustedAttempt(c,fixture.active,op);
  assert.equal(await raw(token,op),200);
  assert.equal(await raw(token,op),401);
  assert.equal(count(id),1);
});
await check('new JTI for Retry, immutable operation bytes/idempotency',async()=>{
  const id=marker(),op=make(id);
  const a=signForTrustedAttempt(c,fixture.active,op).split('.')[1];
  const b=signForTrustedAttempt(c,fixture.active,op).split('.')[1];
  assert.notEqual(JSON.parse(Buffer.from(a,'base64url')).jti,JSON.parse(Buffer.from(b,'base64url')).jti);
  assert.deepEqual(await safe(c,fixture.active,op),{ok:true,code:'OK'});
  assert.deepEqual(await safe(c,fixture.active,op),{ok:false,code:'DENIED'});
  assert.equal(count(id),1);
});
await check('exact method, path percent case, raw query order/percent, whitespace, Unicode',async()=>{
  const variants=[
    [{method:'POST'},{method:'GET'}],
    [{path:'/fixture%2Fpart'},{path:'/fixture%2fpart'}],
    [{query:'a=1&b=%2F'},{query:'b=%2F&a=1'}],
    [{query:'a=%2F'},{query:'a=%2f'}],
    [{body:Buffer.from('{"marker":"M","idempotency_key":"k","question":"مالی"}')},
      {body:Buffer.from('{"marker":"M", "idempotency_key":"k","question":"مالی"}')}],
    [{body:Buffer.from('{"marker":"M","idempotency_key":"k","question":"مالی"}')},
      {body:Buffer.from('{"marker":"M","idempotency_key":"k","question":"مالي"}')}],
  ];
  for(const [signed,wire] of variants){
    const id=marker(),s=make(id,signed),w=make(id,wire);
    const token=signForTrustedAttempt(c,fixture.active,s);
    assert.equal(await raw(token,w),401);
    assert.equal(count(id),0);
  }
});
await check('intact UTF-8 and percent-encoded wire accepted without normalization',async()=>{
  const id=marker();
  const op=make(id,{path:'/fixture%2Fpart',query:'b=%2f&a=%D9%85',
    body:Buffer.from('{"marker":"'+id+'", "idempotency_key":"original-operation", "question":"یک سؤال مالی"}')});
  assert.deepEqual(await safe(c,fixture.active,op),{ok:true,code:'OK'});
  assert.equal(count(id),1);
});
await check('revoked, rotated and expired DB sessions denied',async()=>{
  await new Promise(resolve=>setTimeout(resolve,1800));
  for(const key of ['revoked','rotated','expired']){
    const id=marker();
    assert.deepEqual(await safe(c,fixture[key],make(id)),{ok:false,code:'DENIED'});
    assert.equal(count(id),0);
  }
});
await check('unapproved target, keyless config fail closed',async()=>{
  assert.throws(()=>createServiceSender({...c,upstreamOrigin:'https://127.0.0.1:9443'},async()=>fixture.active));
  assert.throws(()=>createServiceSender({...c,privateKeyPem:''},async()=>fixture.active));
  assert.throws(()=>createServiceSender({...c,clientCertPem:''},async()=>fixture.active));
});
await check('missing mTLS client certificate, invalid client cert, wrong CA denied',async()=>{
  const id=marker(),op=make(id),token=signForTrustedAttempt(c,fixture.active,op);
  assert.equal(await raw(token,op,false),-1);
  const rogue={...c,clientCertPem:load('rogue-client.crt'),clientKeyPem:load('rogue-client.key')};
  assert.deepEqual(await safe(rogue,fixture.active,op),{ok:false,code:'TRANSPORT_FAILURE'});
  assert.deepEqual(await safe({...c,caPem:load('rogue-ca.crt')},fixture.active,op),
    {ok:false,code:'TRANSPORT_FAILURE'});
  assert.equal(count(id),0);
});
await check('hostname mismatch despite same trusted CA rejected',async()=>{
  const bad={...c,upstreamOrigin:'https://localhost:8443',
    allowedOrigins:['https://localhost:8443']};
  const id=marker();
  assert.deepEqual(await safe(bad,fixture.active,make(id)),{ok:false,code:'TRANSPORT_FAILURE'});
  assert.equal(count(id),0);
});
await check('no redirect follow, timeout, malformed 200, truncated stream',async()=>{
  for(const [path,expectCode,settings] of [
    ['/fixture-redirect','REDIRECT_REJECTED',c],
    ['/fixture-timeout','TIMEOUT',{...c,timeoutMs:75}],
    ['/fixture-invalid','INVALID_RESPONSE',c],
    ['/fixture-disconnect','INVALID_RESPONSE',c],
  ]){
    const id=marker(),result=await safe(settings,fixture.active,make(id,{path}));
    assert.equal(result.code,expectCode,path);
    assert.equal(result.ok,false);
    assert.equal(count(id),0);
  }
});

/** Local CI-only TLS transport fixtures; no API verifier or product action. */
function within(promise,limitMs,label){
  let timer;
  const guard=new Promise((_,reject)=>{
    timer=setTimeout(()=>reject(new Error('CI_DEADLINE_TEST_STALLED_'+label)),limitMs);
  });
  return Promise.race([promise,guard]).finally(()=>clearTimeout(timer));
}
function listen(server){
  return new Promise((resolve,reject)=>{
    server.once('error',reject);
    server.listen(0,'127.0.0.1',()=>{
      server.off('error',reject);
      const addr=server.address();
      if(!addr||typeof addr==='string')return reject(new Error('CI_INVALID_LISTENER'));
      resolve(addr.port);
    });
  });
}
function closeServer(server){
  return within(new Promise((resolve,reject)=>server.close(err=>err?reject(err):resolve())),
    3500,'SERVER_CLOSE');
}
let tlsServer;
let responseFirst;
let responseClosed;
let startResponse;
let finishResponse;
let dripWrites=0;
let dripTimer;
const tlsSockets=new Set();
const tlsClosed=[];
try{
  responseFirst=new Promise(resolve=>{startResponse=resolve;});
  responseClosed=new Promise(resolve=>{finishResponse=resolve;});
  tlsServer=createHttpsServer({
    key:load('api.key'),cert:load('api.crt'),ca:load('ca.crt'),
    requestCert:true,rejectUnauthorized:true,
  },(request,response)=>{
    request.resume();
    const requestPath=request.url?.split('?')[0];
    if(requestPath==='/deadline-drip'){
      response.on('close',()=>{
        if(dripTimer)clearInterval(dripTimer);
        finishResponse({destroyed:response.destroyed,finished:response.writableFinished});
      });
      response.setHeader('Content-Type','application/json');
      response.write('{"ok":'); // Headers and first response bytes observed by the client.
      startResponse();
      // Every interval is far below the deadline, while overall time >2x.
      // The old socket-inactivity req.setTimeout would not abort this stream.
      dripTimer=setInterval(()=>{
        if(response.destroyed){clearInterval(dripTimer);return;}
        dripWrites++;
        response.write(' ');
        if(dripWrites===20){clearInterval(dripTimer);response.end('true}');}
      },110);
    }else if(requestPath==='/deadline-fast'){
      response.setHeader('Content-Type','application/json');
      response.end('{"ok":true}');
    }else{
      response.statusCode=404;
      response.end('not-found');
    }
  });
  tlsServer.on('connection',socket=>{
    tlsSockets.add(socket);
    tlsClosed.push(new Promise(resolve=>socket.once('close',()=>{
      tlsSockets.delete(socket);resolve();
    })));
  });
  const port=await listen(tlsServer);
  const localOrigin='https://127.0.0.1:'+port;
  const local={...c,upstreamOrigin:localOrigin,allowedOrigins:[localOrigin],timeoutMs:900};
  await check('complete HTTPS response before absolute deadline remains OK',async()=>{
    const started=performance.now();
    const result=await within(safe(local,fixture.active,make(marker(),{path:'/deadline-fast'})),
      3000,'FAST_RESPONSE');
    assert.deepEqual(result,{ok:true,code:'OK'});
    assert.ok(performance.now()-started<local.timeoutMs,
      'normal response must finish before its own configured deadline');
  });
  await check('HTTPS drip cannot extend total deadline; response and socket closed',async()=>{
    const started=performance.now();
    const sending=safe(local,fixture.active,make(marker(),{path:'/deadline-drip'}));
    await within(responseFirst,3000,'DRIP_FIRST_CHUNK');
    const result=await within(sending,3000,'DRIP_RESULT');
    const duration=performance.now()-started;
    assert.deepEqual(result,{ok:false,code:'TIMEOUT'});
    assert.ok(duration>=local.timeoutMs-160,'deadline was not merely a premature idle timeout');
    assert.ok(duration<3000,'deadline was not postponed until the streaming body completed');
    const closed=await within(responseClosed,3000,'DRIP_RESPONSE_CLOSE');
    assert.equal(closed.destroyed,true);
    assert.equal(closed.finished,false,'server had not finished the body when client aborted');
    assert.ok(dripWrites>=2,'server emitted progressive chunks before abort');
  });
}finally{
  if(dripTimer)clearInterval(dripTimer);
  if(tlsServer){
    await closeServer(tlsServer);
    // Server.close callback may precede the last socket's close event;
    // explicitly wait on every observed socket, not a timing-only sleep.
    await within(Promise.all(tlsClosed),3000,'HTTPS_SOCKET_CLOSE_EVENTS');
  }
}
assert.equal(tlsSockets.size,0,'no HTTPS transport sockets left open');

await check('accepted TCP with stalled TLS handshake hits absolute deadline and closes socket',async()=>{
  let tcpServer;
  let clientSocket;
  let accepted;
  let didAccept;
  let closed;
  let didClose;
  let clientHelloBytes=0;
  try{
    accepted=new Promise(resolve=>{didAccept=resolve;});
    closed=new Promise(resolve=>{didClose=resolve;});
    tcpServer=createTcpServer(socket=>{
      clientSocket=socket;
      // Intentionally accept TCP but NEVER respond to the TLS ClientHello.
      socket.on('error',()=>{});
      // Drain the TLS ClientHello. A permanently paused raw TCP receiver
      // can hide its peer FIN and make close-observation falsely time out.
      socket.on('data',part=>{clientHelloBytes+=part.length;});
      socket.resume();
      socket.once('close',()=>didClose());
      didAccept();
    });
    const port=await listen(tcpServer);
    const origin='https://127.0.0.1:'+port;
    const config={...c,upstreamOrigin:origin,allowedOrigins:[origin],timeoutMs:750};
    const started=performance.now();
    const sending=safe(config,fixture.active,make(marker()));
    await within(accepted,3000,'TCP_CONNECTED_BEFORE_TLS');
    const result=await within(sending,3000,'STALL_TLS_RESULT');
    const duration=performance.now()-started;
    assert.deepEqual(result,{ok:false,code:'TIMEOUT'});
    assert.ok(duration>=config.timeoutMs-160,'TLS failed before the actual deadline');
    assert.ok(duration<3000,'handshake was not allowed to stall beyond the budget');
    await within(closed,3000,'STALL_TLS_SOCKET_CLOSE');
    assert.ok(clientHelloBytes>0,'a real TLS ClientHello was sent before the deadline');
    assert.equal(clientSocket.destroyed,true,'TCP socket must be destroyed at the deadline');
  }finally{
    if(clientSocket&&!clientSocket.destroyed)clientSocket.destroy();
    if(tcpServer)await closeServer(tcpServer);
  }
});

execFileSync('python',['tests/phase3/integration/ui/audit_bff_trust.py','role'],{stdio:'pipe'});
console.log('BFF_HTTPS_MTLS_INTEGRATION_PASS checks='+checks);
