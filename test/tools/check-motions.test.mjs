import assert from 'node:assert/strict';
import {mkdirSync, mkdtempSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import test from 'node:test';
import {clipsOf, problems} from '../../scripts/check-motions.mjs';

const clip = (name, data) => `do local v, i = {${data}},\n    {1,0}\nsmlua_anim_util_register_animation('${name}', 1, 0, 0, 0, 8, v, i)\n`;

function fixture(kickData = '1,2,3', otherData = '4,5') {
  const root = mkdtempSync(join(tmpdir(), 'motions-'));
  for (const d of ['art', 'mod/kid-goku']) mkdirSync(join(root, d), {recursive: true});
  writeFileSync(join(root, 'mod/kid-goku/anims-data.lua'), clip('goku_side_kick_in', kickData) + clip('goku_side_kick2_in', otherData) + clip('goku_jump_38', '9'));
  writeFileSync(join(root, 'art/motions-kept.json'), '{"motions": {}}');
  return root;
}

function keep(root, motion) {
  const list = {motions: {[motion]: {said: 'before looks better', clips: clipsOf(root, motion)}}};
  writeFileSync(join(root, 'art/motions-kept.json'), JSON.stringify(list));
  return root;
}

test('a kept motion as it is holds', () => assert.deepEqual(problems(keep(fixture(), 'side_kick_in')), []));

test('a kept motion changing fails, naming his words', () => {
  const root = keep(fixture(), 'side_kick_in');
  writeFileSync(join(root, 'mod/kid-goku/anims-data.lua'), clip('goku_side_kick_in', '1,2,4') + clip('goku_side_kick2_in', '4,5'));
  assert.match(problems(root).join(), /goku_side_kick_in isn't what Metal Fox kept \("before looks better"\)/);
});

test('a motion is its own clips only: side_kick_in is not side_kick2_in', () => {
  assert.deepEqual(Object.keys(clipsOf(fixture(), 'side_kick_in')), ['goku_side_kick_in']);
  const root = keep(fixture(), 'side_kick_in');
  writeFileSync(join(root, 'mod/kid-goku/anims-data.lua'), clip('goku_side_kick_in', '1,2,3') + clip('goku_side_kick2_in', '7'));
  assert.deepEqual(problems(root), []);
});

test('each length a motion plays at is held', () => assert.deepEqual(Object.keys(clipsOf(fixture(), 'jump')), ['goku_jump_38']));
