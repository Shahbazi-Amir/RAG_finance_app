import test from 'node:test';
import assert from 'node:assert/strict';
import {classifyEvidence} from '../../../apps/web/src/ui/retrieval-evidence-view.ts';

const verified={
  position:1,chunkId:'chunk_from_real_contract_after_api_approval',
  sourceId:'source_from_real_contract_after_api_approval',
  sourceVerified:true,locator:null
};
test('validated C018 source without locator retains IDs but never invents URL',()=>{
  const a=classifyEvidence(verified);
  assert.equal(a.status,'no_web_locator');
  assert.equal(a.href,null);
  assert.equal(a.displayIdentifiers,true);
  assert.match(a.label,/پیوند وب معتبر ندارد/);
});
test('unverified source cannot be called evidence even with HTTPS locator',()=>{
  const a=classifyEvidence({...verified,sourceVerified:false,locator:{
    kind:'url',verified:true,url:'https://example.org/path'
  }});
  assert.equal(a.status,'unverified_source');
  assert.equal(a.href,null);
  assert.equal(a.displayIdentifiers,false);
  assert.match(a.label,/تأیید نشده/);
});
test('unverified destination is not turned into a source link',()=>{
  const a=classifyEvidence({...verified,locator:{
    kind:'url',verified:false,url:'https://example.org/path'
  }});
  assert.equal(a.status,'unverified_destination');
  assert.equal(a.href,null);
  assert.match(a.label,/مقصد تأیید نشده/);
});
test('only explicitly verified safe public HTTPS URL is linkable',()=>{
  const accept=classifyEvidence({...verified,locator:{
    kind:'url',verified:true,url:'https://example.org/evidence'
  }});
  assert.equal(accept.status,'verified_link');
  assert.equal(accept.href,'https://example.org/evidence');
  const invalid=[
    'javascript:alert(1)','http://example.org/',
    'https://u:p@example.org/private','https://127.0.0.1/',
    'https://localhost/','https://foo.local/','https://example.org:9443',
    'https://[::1]/','https://example.org/#secrets',
  ];
  for(const url of invalid){
    const x=classifyEvidence({...verified,locator:{kind:'url',verified:true,url}});
    assert.equal(x.href,null,url);
    assert.equal(x.status,'unverified_destination',url);
  }
});
test('document location and transcript time are not invented as URLs',()=>{
  const book=classifyEvidence({...verified,locator:{
    kind:'book_page',verified:true,page:12
  }});
  assert.equal(book.href,null);assert.equal(book.locationText,'صفحهٔ ثبت‌شده: 12');
  const transcript=classifyEvidence({...verified,locator:{
    kind:'transcript_timestamp',verified:true,timestampMs:0
  }});
  assert.equal(transcript.href,null);
  assert.equal(transcript.locationText,'زمان ثبت‌شده (میلی‌ثانیه): 0');
  assert.equal(classifyEvidence({...verified,locator:{
    kind:'book_page',verified:true,page:-2
  }}).status,'unverified_destination');
});
test('invalid/duplicate/unbounded row positions cannot be displayed as verified',()=>{
  for(const position of [0,11,1.5,Number.NaN,Number.MAX_SAFE_INTEGER]){
    assert.equal(classifyEvidence({...verified,position}).status,'unverified_source');
  }
  assert.equal(classifyEvidence({...verified,sourceId:''}).status,'unverified_source');
  assert.equal(classifyEvidence({...verified,chunkId:''}).status,'unverified_source');
});
