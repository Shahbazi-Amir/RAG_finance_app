import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const draft=JSON.parse(readFileSync(new URL('./fixtures/ui-f3-contract-candidates.v0_1.json',import.meta.url),'utf8'));
test('UI-04/09/13/10 draft fixtures must never imply an approved or shipped API',()=>{
  assert.equal(draft.schema_status,'PROPOSED_NOT_APPROVED');
  assert.equal(draft.fixture_only,true);
  assert.equal(draft.approved,false);
  assert.equal(draft.wire_contract_enabled,false);
  assert.equal(draft.version,'ui.f3.review_candidates.v0_1');
  assert.equal(new Set(draft.fixtures.map(x=>x.id)).size,4);
  for(const item of draft.fixtures){
    assert.match(item.kind,/^ui\.(consent|feedback|deletion|stream)\.candidate\.v0_1$/);
    assert.equal(item.actor,'SIGNED_BFF_OWNER_ONLY');
    assert.ok(item.blocked_on);
    assert.equal(item.request?.owner_id,undefined);
    assert.equal(item.request?.user_id,undefined);
    assert.equal(item.response?.committed??item.cancel_response?.committed,false);
  }
});
test('pending consent and deletion, declined foreign feedback, cancel requested are not successes',()=>{
  const byId=Object.fromEntries(draft.fixtures.map(x=>[x.id,x]));
  assert.equal(byId.CONSENT_WITHDRAWAL.response.state,'PENDING');
  assert.equal(byId.FEEDBACK_WRONG_ANSWER.response.state,'REJECTED');
  assert.equal(byId.DELETE_REQUEST_NOT_COMPLETE.response.state,'DELETE_REQUESTED');
  assert.equal(byId.STREAM_CANCEL_IS_NOT_CANCELLED.cancel_response.state,'CANCEL_REQUESTED');
  const events=byId.STREAM_CANCEL_IS_NOT_CANCELLED.events;
  assert.deepEqual(events.map(x=>x.sequence),[1,2]);
  assert.ok(events.every(x=>x.fixture_only===true));
  assert.ok(!events.some(x=>x.state==='COMMITTED'));
});
test('actual contracted Product v1 and retrieved source v1 stay separate from draft DTO',()=>{
  const product=JSON.parse(readFileSync(new URL('../../../packages/contracts/product.v1.schema.json',import.meta.url),'utf8'));
  const sources=JSON.parse(readFileSync(new URL('../../../packages/contracts/api.retrieved_sources.v1.schema.json',import.meta.url),'utf8'));
  assert.equal(product.$id,'urn:ragfinance:product:v1');
  assert.equal(sources.$id,'urn:rag-finance:api.retrieved_sources.v1');
  assert.equal(sources.properties.contract_version.const,'api.retrieved_sources.v1');
  assert.equal(sources.additionalProperties,false);
  assert.ok(!JSON.stringify(product).includes('ui.consent.candidate.v0_1'));
  assert.ok(!JSON.stringify(sources).includes('ui.stream.candidate.v0_1'));
});
