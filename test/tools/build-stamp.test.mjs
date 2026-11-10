import assert from 'node:assert/strict';
import {mkdirSync, mkdtempSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import test from 'node:test';
import {stampArt, staleReason, writeStamp} from '../../scripts/build-stamp.mjs';

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'stamp-'));
  for (const d of ['scripts/blender', 'art/faces']) mkdirSync(join(root, d), {recursive: true});
  writeFileSync(join(root, 'scripts/blender/body.py'), 'a');
  writeFileSync(join(root, 'scripts/build.mjs'), 'b');
  writeFileSync(join(root, 'art/faces/yell.svg'), 'c');
  return root;
}

test('nothing built is stale', () => assert.match(staleReason(fixture()), /nothing has been built/));

test('a good build is fresh', () => { const root = fixture(); writeStamp(root); assert.equal(staleReason(root), null); });

test('a model script changing after the build is stale', () => {
  const root = fixture();
  writeStamp(root);
  writeFileSync(join(root, 'scripts/blender/body.py'), 'changed');
  assert.match(staleReason(root), /scripts changed/);
});

test('art changing is stale until it is repainted', () => {
  const root = fixture();
  writeStamp(root);
  writeFileSync(join(root, 'art/faces/yell.svg'), 'changed');
  assert.match(staleReason(root), /faces changed/);
  stampArt(root);
  assert.equal(staleReason(root), null);
});

test('repainting does not hide a changed script', () => {
  const root = fixture();
  writeStamp(root);
  writeFileSync(join(root, 'scripts/blender/body.py'), 'changed');
  stampArt(root);
  assert.match(staleReason(root), /scripts changed/);
});
