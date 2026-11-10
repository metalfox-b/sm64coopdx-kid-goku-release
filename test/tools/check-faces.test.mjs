import assert from 'node:assert/strict';
import {mkdirSync, mkdtempSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import test from 'node:test';
import {problems, record, shadowChanged} from '../../scripts/check-faces.mjs';

function fixture(shapes = '{"cheer": (1.3, 1.1)}', worn = 'DETERMINED, DETERMINED, SHOUT, SURPRISED, DETERMINED') {
  const root = mkdtempSync(join(tmpdir(), 'faces-'));
  for (const d of ['art/faces', 'scripts', 'mod/kid-goku']) mkdirSync(join(root, d), {recursive: true});
  for (const n of ['cheer', 'determined', 'shout', 'surprised']) writeFileSync(join(root, 'art/faces', `${n}.svg`), `<svg>${n}</svg>`);
  writeFileSync(join(root, 'scripts/face_shapes.py'), `SHAPES = ${shapes}\n`);
  writeFileSync(join(root, 'mod/kid-goku/f-face.lua'), `local GRIT, FIERCE, YELL, HIT, GRIN = ${worn}\n`);
  writeFileSync(join(root, 'art/faces/shadow.svg'), '<svg>shadow</svg>');
  writeFileSync(join(root, 'scripts/faces.py'), 'SKIN_SHADOW = (1, 2, 3)\n');
  mkdirSync(join(root, 'mod/kid-goku/actors/goku'), {recursive: true});
  for (const n of ['cheer', 'determined', 'shout', 'surprised']) writeFileSync(join(root, `mod/kid-goku/actors/goku/goku_face_${n}.ci4.png`), n);
  writeFileSync(join(root, 'art/faces/passed.json'), '{"faces": {}}');
  return root;
}

function passedAll(root) { for (const n of ['cheer', 'determined', 'shout', 'surprised']) record(root, 'pass', n, 'yes'); return root; }

test('passed faces as they are hold', () => assert.deepEqual(problems(passedAll(fixture())), []));

test("a passed face's art changing fails", () => {
  const root = passedAll(fixture());
  writeFileSync(join(root, 'art/faces/shout.svg'), '<svg>new</svg>');
  assert.match(problems(root).join(), /shout: its art/);
});

test("a passed face's head changing fails", () => {
  const root = passedAll(fixture());
  writeFileSync(join(root, 'scripts/face_shapes.py'), 'SHAPES = {"cheer": (1.3, 1.1), "shout": (1.1, 1.08)}\n');
  assert.match(problems(root).join(), /shout: its head/);
});

test('an unpassed face with a head of its own fails', () => {
  const root = passedAll(fixture('{"cheer": (1.3, 1.1), "yell": (1.22, 1.15)}'));
  assert.match(problems(root).join(), /yell: has a head/);
});

test('wearing an unpassed fight face fails, and a passed one holds', () => {
  assert.match(problems(passedAll(fixture(undefined, 'DETERMINED, DETERMINED, 14, SURPRISED, DETERMINED'))).join(), /yell: wears 14/);
  const root = passedAll(fixture(undefined, 'DETERMINED, DETERMINED, 14, SURPRISED, DETERMINED'));
  writeFileSync(join(root, 'art/faces/yell.svg'), '<svg>yell</svg>');
  record(root, 'pass', 'yell', 'yes');
  assert.deepEqual(problems(root), []);
});

test('unlocking needs his words and lets the art change', () => {
  const root = passedAll(fixture(undefined, 'DETERMINED, DETERMINED, DETERMINED, SURPRISED, DETERMINED'));
  assert.throws(() => record(root, 'unlock', 'shout'), /said/);
  record(root, 'unlock', 'shout', 'fix both please');
  writeFileSync(join(root, 'art/faces/shout.svg'), '<svg>new</svg>');
  assert.deepEqual(problems(root), []);
});

test("a passed face's painted texture changing fails, whatever changed it", () => {
  const root = passedAll(fixture());
  writeFileSync(join(root, 'mod/kid-goku/actors/goku/goku_face_shout.ci4.png'), 'repainted');
  assert.match(problems(root).join(), /shout: its painted texture/);
});

test('the shadow every face shares changing fails', () => {
  const root = passedAll(fixture());
  writeFileSync(join(root, 'art/faces/shadow.svg'), '<svg>a bigger one</svg>');
  assert.match(problems(root).join(), /shadow every face shares/);
  const again = passedAll(fixture());
  writeFileSync(join(again, 'scripts/faces.py'), 'SKIN_SHADOW = (9, 9, 9)\n');
  assert.match(problems(again).join(), /shadow every face shares/);
});

test('a shadow change he asked for needs his words, takes the new textures, and still holds their art', () => {
  const root = passedAll(fixture());
  writeFileSync(join(root, 'art/faces/shadow.svg'), '<svg></svg>');
  writeFileSync(join(root, 'mod/kid-goku/actors/goku/goku_face_shout.ci4.png'), 'repainted');
  assert.throws(() => shadowChanged(root), /said/);
  shadowChanged(root, 'please fix those graphics faults');
  assert.deepEqual(problems(root), []);
  writeFileSync(join(root, 'art/faces/shout.svg'), '<svg>new</svg>');
  assert.match(problems(root).join(), /shout: its art/);
});

test('tracing a face from a frame he rejected fails, and only for that face', () => {
  const root = passedAll(fixture());
  writeFileSync(join(root, 'art/faces/rejected.json'), JSON.stringify({frames: [{frame: 'bad.jpg', faces: ['yell']}, {frame: 'old.png', faces: 'all', until_retraced: ['grit']}]}));
  writeFileSync(join(root, 'scripts/trace_faces.py'), 'f = Face("yell", "bad.jpg", (1, 2))\nf = Face("hit", "bad.jpg", (1, 2))\nf = Face("grit", "old.png", (1, 2))\n');
  assert.deepEqual(problems(root).filter(p => /rejected/.test(p)), ['yell: traced from bad.jpg, which Metal Fox rejected']);
});
