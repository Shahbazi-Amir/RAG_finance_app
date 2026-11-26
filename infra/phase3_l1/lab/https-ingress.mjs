// CI-only sole HTTPS ingress. No proxying arbitrary destinations.
import https from 'node:https';
import http from 'node:http';
import fs from 'node:fs';
const root='/run/ingress/';
const proof=fs.readFileSync(root+'proof','utf8').trim();
if(proof.length<32)process.exit(78);
const denied=['connection','proxy-connection','keep-alive','transfer-encoding','te','trailer','upgrade','proxy-authenticate','proxy-authorization','forwarded'];
const server=https.createServer({key:fs.readFileSync(root+'ingress.key'),cert:fs.readFileSync(root+'ingress.crt'),minVersion:'TLSv1.2'},(req,res)=>{
  if(req.headers.host!=='ragfinance.ir'||!req.url?.startsWith('/')||req.url.startsWith('//')){
    res.writeHead(421,{'cache-control':'no-store'});res.end();return;
  }
  const headers={};
  const nominated=String(req.headers.connection??'').toLowerCase().split(',').map(x=>x.trim());
  for(const [k,v] of Object.entries(req.headers)){
    if(!denied.includes(k)&&!nominated.includes(k)&&!k.startsWith('x-forwarded-')&&!k.startsWith('x-auth-')&&k!=='host')headers[k]=v;
  }
  Object.assign(headers,{host:'ragfinance.ir','x-forwarded-host':'ragfinance.ir','x-forwarded-proto':'https','x-auth-staging-proxy-proof':proof});
  const upstream=http.request({hostname:'web',port:3000,path:req.url,method:req.method,headers,timeout:15000},reply=>{
    const output={...reply.headers};for(const k of denied)delete output[k];
    res.writeHead(reply.statusCode??502,output);reply.pipe(res);
  });
  upstream.on('timeout',()=>upstream.destroy());
  upstream.on('error',()=>{if(!res.headersSent)res.writeHead(503,{'cache-control':'no-store'});res.end();});
  req.on('aborted',()=>upstream.destroy());
  req.pipe(upstream);
});
server.requestTimeout=20000;server.headersTimeout=10000;
server.listen(443,'0.0.0.0');
