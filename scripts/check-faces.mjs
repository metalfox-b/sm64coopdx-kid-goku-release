import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {existsSync, readFileSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const sha = text => createHash('sha256').update(text).digest('hex');
const listOf = root => join(root, 'art', 'faces', 'passed.json');
const textureOf = (root, name) => join(root, 'mod', 'kid-goku', 'actors', 'goku', `goku_face_${name}.ci4.png`);
const sharedOf = root => sha(readFileSync(join(root, 'art', 'faces', 'shadow.svg'))) + (/^SKIN_SHADOW = .*$/m.exec(readFileSync(join(root, 'scripts', 'faces.py'), 'utf8'))?.[0] ?? '');

export function headsIn(root) {
  const source = readFileSync(join(root, 'scripts', 'face_shapes.py'), 'utf8');
  const block = /^SHAPES = \{([^}]*)\}/m.exec(source);
  if (!block) throw new Error('scripts/face_shapes.py has no SHAPES');
  return Object.fromEntries([...block[1].matchAll(/"(\w+)": \(([\d.]+), ([\d.]+)\)/g)].map(m => [m[1], [+m[2], +m[3]]]));
}

export function problems(root) {
  const list = JSON.parse(readFileSync(listOf(root), 'utf8'));
  const passed = list.faces;
  const heads = headsIn(root);
  const found = [];
  if (list.shared && sharedOf(root) !== list.shared) found.push("the shadow every face shares isn't what Metal Fox passed them with");
  for (const [name, face] of Object.entries(passed)) {
    const art = join(root, 'art', 'faces', `${name}.svg`);
    if (!existsSync(art)) { found.push(`${name}: passed, and its art is gone`); continue; }
    if (sha(readFileSync(art)) !== face.svg) found.push(`${name}: its art isn't what Metal Fox passed`);
    if (JSON.stringify(heads[name] ?? null) !== JSON.stringify(face.head)) found.push(`${name}: its head isn't the one Metal Fox passed`);
    if (face.texture && existsSync(textureOf(root, name)) && sha(readFileSync(textureOf(root, name))) !== face.texture) found.push(`${name}: its painted texture isn't what Metal Fox passed`);
  }
  for (const name of Object.keys(heads)) if (!passed[name]) found.push(`${name}: has a head of its own and Metal Fox hasn't passed it`);
  const rejectedPath = join(root, 'art', 'faces', 'rejected.json');
  const tracer = join(root, 'scripts', 'trace_faces.py');
  if (existsSync(rejectedPath) && existsSync(tracer)) {
    const uses = [...readFileSync(tracer, 'utf8').matchAll(/Face\("(\w+)", "([^"]+)"/g)];
    for (const {frame, faces, until_retraced: waiting = []} of JSON.parse(readFileSync(rejectedPath, 'utf8')).frames) {
      for (const [, name, used] of uses) {
        if (used === frame && (faces === 'all' || faces.includes(name)) && !waiting.includes(name)) found.push(`${name}: traced from ${frame}, which Metal Fox rejected`);
      }
    }
  }
  const lua = readFileSync(join(root, 'mod', 'kid-goku', 'f-face.lua'), 'utf8');
  const worn = /^local GRIT, FIERCE, YELL, HIT, GRIN = (.+)$/m.exec(lua);
  if (!worn) found.push("f-face.lua: can't find its fight faces");
  else {
    const stands = worn[1].split(',').map(s => s.trim());
    ['grit', 'fierce', 'yell', 'hit', 'grin'].forEach((name, i) => {
      const value = stands[i] ?? '';
      const face = /^\d+$/.test(value) ? name : value.toLowerCase();
      if (!passed[face]) found.push(`${name}: wears ${value} in play, and Metal Fox hasn't passed that`);
    });
  }

  const glance = /^local YELL_LEFT, YELL_RIGHT = (.+)$/m.exec(lua);
  if (glance) glance[1].split(',').map(s => s.trim()).forEach((value, i) => {
    const name = ['yell_left', 'yell_right'][i];
    if (/^\d+$/.test(value) && !passed[name]) found.push(`${name}: worn on a side kick, and Metal Fox hasn't passed it`);
  });
  return found;
}

export function record(root, verb, name, said) {
  if (!said) throw new Error(`--${verb} needs --said with Metal Fox's words`);
  const list = JSON.parse(readFileSync(listOf(root), 'utf8'));
  list.log ??= [];
  list.log.push({[verb]: name, said, on: new Date().toISOString().slice(0, 10)});
  if (verb === 'unlock') {
    if (!list.faces[name]) throw new Error(`${name} isn't on the list`);
    delete list.faces[name];
  } else {
    const art = readFileSync(join(root, 'art', 'faces', `${name}.svg`));
    list.faces[name] = {svg: sha(art), head: headsIn(root)[name] ?? null};
    if (existsSync(textureOf(root, name))) list.faces[name].texture = sha(readFileSync(textureOf(root, name)));
    list.shared = sharedOf(root);
  }
  writeFileSync(listOf(root), JSON.stringify(list, null, 1) + '\n');
}

export function shadowChanged(root, said) {
  if (!said) throw new Error("--shadow-changed needs --said with Metal Fox's words");
  const list = JSON.parse(readFileSync(listOf(root), 'utf8'));
  list.log ??= [];
  list.log.push({shadow_changed: true, said, on: new Date().toISOString().slice(0, 10)});
  list.shared = sharedOf(root);
  for (const [name, face] of Object.entries(list.faces)) if (existsSync(textureOf(root, name))) face.texture = sha(readFileSync(textureOf(root, name)));
  writeFileSync(listOf(root), JSON.stringify(list, null, 1) + '\n');
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = join(dirname(fileURLToPath(import.meta.url)), '..');
  const arg = name => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : undefined; };
  if (process.argv.includes('--shadow-changed')) { shadowChanged(root, arg('--said')); console.log('shadow change recorded'); process.exit(0); }
  for (const verb of ['pass', 'unlock']) if (arg(`--${verb}`)) { record(root, verb, arg(`--${verb}`), arg('--said')); console.log(`${verb}: ${arg(`--${verb}`)}`); process.exit(0); }
  let hooks = '';
  try { hooks = execFileSync('git', ['-C', root, 'config', 'core.hooksPath'], {encoding: 'utf8'}).trim(); } catch {}
  if (hooks !== 'scripts/hooks') console.log('note: hooks are off. Turn them on with: git config core.hooksPath scripts/hooks');
  const found = problems(root);
  for (const line of found) console.log(`FAIL ${line}`);
  if (found.length) { console.log('A face changes only when Metal Fox asks: --unlock it with his words first, and --pass it once he has.'); process.exit(1); }
  console.log('faces hold');
}
