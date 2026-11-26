"""Execute exact JS witness in Node using deterministic async fetch doubles.
No browser/network/product claim. Requires Node for this separate local test.
"""
import json,shutil,subprocess,unittest
from f3_lab_read_load import JS

HARNESS=r'''
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const {role,width,rounds,fault}=input;
let cancelled=0;
let active=0,peak=0,count=0;
const context={performance,AbortController,setTimeout,clearTimeout,encodeURIComponent,TextDecoder,
  fetch:async(path,opts)=>{
    if(opts.method!=='GET'||opts.credentials!=='same-origin'||opts.cache!=='default'||opts.redirect!=='error'||!opts.signal)throw Error('unsafe-options');
    if(!path.startsWith('/api/history/conversations'))throw Error('unexpected-path');
    active++;count++;peak=Math.max(active,peak);
    try {
      await new Promise(r=>setTimeout(r,2));
      const url=new URL(path,'https://fixture.invalid');
      let status=200,body={};
      if(url.searchParams.has('cursor') && role==='a' && url.searchParams.get('cursor')==='fixture-cursor-a'){body={scope_user_id:'owner-a',items:[{conversation_id:fault==='page'?'wrong':'browser-a-1'}],page:{has_more:false}};}
      else if(url.searchParams.has('cursor')||url.searchParams.getAll('limit').length!==1){status=fault==='cursor'?200:422;}
      else if(fault==='unavailable'){status=503;}
      else if(url.pathname.endsWith('/messages')){
        const isB=url.pathname.includes('browser-b-1');
        if((role==='b')!==isB){status=404;body={error:fault==='foreign'?'lab browser A':'NOT_FOUND'};}
        else body={owner_user_id:'owner-'+role,items:[{message_id:'browser-msg-'+role,text:'lab browser '+role.toUpperCase()}]};
      }else{
        body={scope_user_id:fault==='owner'?'wrong':'owner-'+role,
          items:(role==='a'?['browser-a-3','browser-a-2']:['browser-b-1']).map(conversation_id=>({conversation_id})),
          page:{has_more:role==='a',next_cursor:role==='a'?'fixture-cursor-a':null}};
      }
      const bytes=new TextEncoder().encode(JSON.stringify(body));
      let chunks=0;
      const stream=new ReadableStream({pull(c){
        if(fault==='stream-limit'){c.enqueue(new Uint8Array(65536));return;}
        if(chunks++===0)c.enqueue(fault==='invalid-utf8'?new Uint8Array([255]):bytes);else c.close();
      },cancel(){cancelled++;}});
      return {status,headers:{get:k=>k==='cache-control'?(fault==='cache'?'public':'no-store'):k==='content-length'&&fault==='length-limit'?'999999':null},body:stream};
    }finally{active--;}
  }};
(async()=>{
  try{
    const fn=vm.runInNewContext('('+input.js+')',context);
    const r=await fn({role,owner:'owner-'+role,width,rounds,checkCursor:input.checkCursor,extraChecks:input.extraChecks});
    console.log(JSON.stringify({ok:true,result:r,count,peak,active,cancelled}));
  }catch(e){console.log(JSON.stringify({ok:false,error:e.message,count,peak,active,cancelled}));}
})();
'''

@unittest.skipUnless(shutil.which('node'),'Node required')
class Tests(unittest.TestCase):
    def call(self,role='a',width=4,rounds=3,fault=None,cursor=None,extra=False):
        p=subprocess.run(['node','-e',HARNESS],input=json.dumps(dict(js=JS,role=role,width=width,rounds=rounds,fault=fault,checkCursor=cursor,extraChecks=extra)),text=True,capture_output=True,timeout=10,check=True)
        return json.loads(p.stdout)
    def test_parallel_exact_js(self):
        a=self.call();self.assertTrue(a['ok']);self.assertEqual(a['count'],12);self.assertEqual(a['peak'],4);self.assertEqual(a['active'],0)
        b=self.call('b',cursor=a['result']['cursor']);self.assertTrue(b['ok']);self.assertEqual(b['count'],15);self.assertEqual(b['result']['statuses'],{'200':6,'404':6,'422':3})
    def test_one_and_two(self):
        for n in (1,2):
            r=self.call(width=n);self.assertTrue(r['ok']);self.assertEqual(r['peak'],n)
    def test_faults_fail_closed_after_all_settled(self):
        for fault,role in [('cache','a'),('owner','a'),('foreign','b'),('unavailable','a')]:
            with self.subTest(fault=fault):
                r=self.call(role,fault=fault);self.assertFalse(r['ok']);self.assertEqual(r['active'],0);self.assertGreater(r['count'],0)
    def test_cross_cursor_success_is_failure(self):
        r=self.call('b',fault='cursor',cursor='fixture-cursor-a');self.assertFalse(r['ok']);self.assertEqual(r['error'],'negative');self.assertEqual(r['count'],13)

    def test_default_cache_and_bidirectional_details(self):
        a=self.call(extra=True);self.assertTrue(a['ok']);self.assertEqual(a['result']['statuses'],{'200':15,'404':1})
        b=self.call('b',cursor=a['result']['cursor'],extra=True);self.assertTrue(b['ok']);self.assertEqual(b['result']['statuses'],{'200':9,'404':7,'422':3})
    def test_page_replay_bad_id_rejected(self):
        self.assertFalse(self.call(extra=True,fault='page')['ok'])
    def test_stream_limit_cancels(self):
        r=self.call(width=1,fault='stream-limit');self.assertFalse(r['ok']);self.assertGreaterEqual(r['cancelled'],1)
    def test_content_length_limit_cancels(self):
        r=self.call(width=1,fault='length-limit');self.assertFalse(r['ok']);self.assertGreaterEqual(r['cancelled'],1)
    def test_invalid_utf8_denied(self):
        self.assertFalse(self.call(width=1,fault='invalid-utf8')['ok'])

if __name__=='__main__':unittest.main()
