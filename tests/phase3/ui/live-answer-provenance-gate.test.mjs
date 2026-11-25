import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {isVerifiedLiveAnswer} from '../../../apps/web/src/ui/answer-visibility.ts';
import {verifiedSourceUrl} from '../../../apps/web/src/ui/source-locator.ts';

const registry=JSON.parse(readFileSync(new URL(
  '../../../packages/contracts/fixtures/product.v1.cases.json',import.meta.url),'utf8')).cases;
const fixture=registry.find(x=>x.case_id==='valid_answer_unresolved_source');
assert.ok(fixture?.expected_valid);
function live(){
  const answer=structuredClone(fixture.document);
  answer.provenance={
    origin:'LIVE_VERIFIED',producer_reference:'ci-verified-producer',
    source_fingerprint:'a'.repeat(64),
    rag_binding:{status:'verified',blocked_by:null,
      release_id:'test_release_1',adapter_verified:true}
  };
  answer.citations[0].source={
    ...answer.citations[0].source,
    resolution_status:'verified',attribution_status:'verified',
    source_type:'website',source_id:'source_1',
    display_title_origin:'source_record',
    locator:{kind:'url',url:'https://example.org/safe-evidence',
      page:null,timestamp_ms:null}
  };
  return answer;
}
test('only fully bound LIVE_VERIFIED claim + matching website locator may display',()=>{
  const good=live();
  assert.equal(isVerifiedLiveAnswer(good),true);
  assert.equal(verifiedSourceUrl(good.citations[0].source),'https://example.org/safe-evidence');
  const broken=structuredClone(good);
  broken.citations[0].source.source_type='book';
  assert.equal(isVerifiedLiveAnswer(broken),false);
  assert.equal(verifiedSourceUrl(broken.citations[0].source),null);
  broken.citations[0].source.source_type='website';
  broken.citations[0].source.source_id=null;
  assert.equal(isVerifiedLiveAnswer(broken),false);
});
test('API-looking verified flags cannot compensate for missing verified release identity',()=>{
  const good=live();
  for(const mutate of [
    v=>{v.provenance.rag_binding.release_id=null;},
    v=>{v.provenance.rag_binding.release_id='bad release';},
    v=>{v.provenance.rag_binding.blocked_by='NB23';},
    v=>{v.provenance.producer_reference=null;},
    v=>{v.provenance.producer_reference='  ';},
    v=>{v.provenance.source_fingerprint=null;},
    v=>{v.provenance.source_fingerprint='b'.repeat(63);},
    v=>{v.provenance.rag_binding.adapter_verified=false;},
    v=>{v.provenance.origin='SYNTHETIC';}
  ]){
    const bad=structuredClone(good);mutate(bad);
    assert.equal(isVerifiedLiveAnswer(bad),false,JSON.stringify(bad.provenance));
  }
});
test('NO_ANSWER and CLARIFICATION are citable-free; injected claims never render',()=>{
  const good=live();
  for(const outcome of ['no_answer','clarification','refusal']){
    const safe={...structuredClone(good),outcome,claims:[],citations:[],
      state:'completed',answer_text:'نیازمند ارزیابی مستقل'};
    assert.equal(isVerifiedLiveAnswer(safe),true,outcome);
    const forged=structuredClone(safe);forged.claims=good.claims;
    assert.equal(isVerifiedLiveAnswer(forged),false,outcome+' injected claim');
    const injected=structuredClone(safe);injected.citations=good.citations;
    assert.equal(isVerifiedLiveAnswer(injected),false,outcome+' injected citation');
  }
  for(const outcome of ['unknown','cancelled','error']){
    const safe={...structuredClone(good),outcome,claims:[],citations:[],
      state:outcome==='error'?'failed':outcome,answer_text:null};
    assert.equal(isVerifiedLiveAnswer(safe),true);
    const forged={...safe,answer_text:'محتوای ادعایی ممنوع'};
    assert.equal(isVerifiedLiveAnswer(forged),false);
  }
});
