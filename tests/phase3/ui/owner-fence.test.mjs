import test from 'node:test';
import assert from 'node:assert/strict';
import {OwnerFence} from '../../../apps/web/src/ui/owner-fence.ts';

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
