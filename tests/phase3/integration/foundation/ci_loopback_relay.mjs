/** CI-only raw TCP relay for an unchanged loopback BFF/Bootstrap profile.
 * No TLS termination, HTTP handling, signing, header injection or forwarding
 * to arbitrary destinations. Runs only in the private Web network namespace.
 */
import net from 'node:net';
if(process.env.CI!=='true')throw new Error('CI_ONLY');
const p=JSON.parse(process.env.F3_CI_RELAY??'null');
if(!p||Object.keys(p).sort().join(',')!=='api_host,idp_port,product_port'||
   !/^api-restored-[a-f0-9]{32}$/.test(p.api_host)||
   ![p.product_port,p.idp_port].every(x=>Number.isInteger(x)&&x>=1024&&x<=65535)||
   new Set([p.product_port,p.idp_port,3000,3443,3444]).size!==5)
  throw new Error('CI_RELAY_DENIED');
const specs=[
 ['127.0.0.1',p.product_port,p.api_host,8443],
 ['127.0.0.1',p.idp_port,'f3-ci-idp',8080],
 ['0.0.0.0',3444,'127.0.0.1',3443],
];
for(const [bind,port,host,target] of specs){
 const server=net.createServer(client=>{
   const upstream=net.createConnection({host,port:target});
   client.on('error',()=>upstream.destroy());
   upstream.on('error',()=>client.destroy());
   client.on('close',()=>upstream.destroy());
   upstream.on('close',()=>client.destroy());
   client.pipe(upstream);upstream.pipe(client);
 });
 server.on('error',()=>process.exit(78));
 server.listen(port,bind);
}
