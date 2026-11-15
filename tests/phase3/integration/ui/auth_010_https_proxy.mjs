/** Isolated HTTPS termination for Next CI browser checks; NEVER production. */
import {createServer} from 'node:https';
import {request as forward} from 'node:http';
import {readFileSync} from 'node:fs';
if(process.env.CI!=='true'||!process.env.AUTH_CI_PROXY_SECRET ||
   process.env.AUTH_CI_PROXY_SECRET.length<32)throw new Error('CI_ONLY');
const server=createServer({
  key:readFileSync(process.env.AUTH_CI_TLS_KEY),
  cert:readFileSync(process.env.AUTH_CI_TLS_CERT),
},(client,response)=>{
  const headers={...client.headers};
  // Always replace, never trust client-supplied proxy proof.
  delete headers['x-auth-ci-proxy-proof'];
  headers['x-auth-ci-proxy-proof']=process.env.AUTH_CI_PROXY_SECRET;
  headers.host='127.0.0.1:3000';
  // API #50 pins /callback in both Code authorization and exchange.
  // Map ONLY that exact CI loopback callback to Next's actual callback route.
  const original=client.url??'';
  const path=process.env.AUTH_CI_DEMO_MODE==='true'&&
    (original==='/callback'||original.startsWith('/callback?'))
    ?'/api/auth/callback'+original.slice('/callback'.length)
    :original;
  const upstream=forward({host:'127.0.0.1',port:3000,method:client.method,
    path,headers},reply=>{
    response.writeHead(reply.statusCode??502,reply.headers);
    reply.pipe(response);
  });
  upstream.on('error',()=>{
    if(!response.headersSent)response.writeHead(502);
    response.end();
  });
  client.pipe(upstream);
});
server.listen(3443,'127.0.0.1',()=>console.log('AUTH_CI_HTTPS_PROXY_READY'));
