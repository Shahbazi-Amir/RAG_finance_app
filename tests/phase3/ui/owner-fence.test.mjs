import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {OwnerFence,sameOwnerPrivacyEpoch} from '../../../apps/web/src/ui/owner-fence.ts';

test('first validated page establishes owner; switching owner never rebinds',()=>{
  const f=new OwnerFence();
  assert.equal(f.observe('owner_A'),true);
  assert.equal(f.observe('owner_A'),true);
  assert.equal(f.observe('owner_B'),false);
  assert.equal(f.observe('owner_A'),true);
});
test('late requests are stale after 401/revoke or owner mismatch invalidation',async()=>{
  const f=new OwnerFence();
  assert.ok(f.observe('owner_A'));
  const captured=f.capture();
  let release=()=>{};
  const oldPending=new Promise(resolve=>{release=resolve});
  const late=oldPending.then(()=>f.current(captured)&&f.observe('owner_A'));
  assert.equal(f.observe('owner_B'),false);
  f.invalidate();
  release();
  assert.equal(await late,false);
  assert.equal(f.current(captured),false);
  assert.equal(f.observe('owner_B'),true);
});
test('blank/untrusted owner is not silently accepted',()=>{
  const f=new OwnerFence();
  assert.equal(f.observe(''),false);
  assert.equal(f.observe('x'),true);
  assert.equal(f.observe(''),false);
});

test('delayed Send receipt remains invisible after 503, 401 or owner rotation',async()=>{
  const fence=new OwnerFence();
  assert.equal(fence.observe('owner_A'),true);
  const ownerRevision=fence.capture();
  let privacy=3;
  const allowed=()=>sameOwnerPrivacyEpoch(fence,ownerRevision,3,privacy);
  assert.equal(allowed(),true);
  let resolve=()=>{};
  const pending=new Promise(done=>{resolve=done;});
  const oldReceipt=pending.then(()=>allowed()?'VISIBLE':'DISCARDED');
  // A signed list GET now failed to revalidate its owner. The result of
  // the old POST may still arrive but may NOT repopulate private UI state.
  privacy++;
  resolve();
  assert.equal(await oldReceipt,'DISCARDED');
  assert.equal(allowed(),false);
  assert.equal(fence.observe('owner_B'),false);
  fence.invalidate();
  assert.equal(fence.observe('owner_B'),true);
  assert.equal(allowed(),false);
  assert.equal(sameOwnerPrivacyEpoch(fence,fence.capture(),privacy,privacy),true);
  assert.equal(sameOwnerPrivacyEpoch(fence,fence.capture(),-1,-1),false);
});
test('actual ProductChat wires privacy+owner receipt AND failure boundaries',()=>{
  const source=readFileSync(new URL(
    '../../../apps/web/src/ui/product-chat.tsx',import.meta.url),'utf8');
  assert.match(source,/const privacyAtStart=privacyEpoch\.current;/);
  assert.match(source,/const ownerRevision=ownerFence\.current\.capture\(\);/);
  assert.equal((source.match(/sameOwnerPrivacyEpoch\(ownerFence\.current,/g)||[]).length,2);
  assert.match(source,/const receipt=await sendMessage\(request\);[^]*?sameOwnerPrivacyEpoch\(ownerFence\.current,/);
});
