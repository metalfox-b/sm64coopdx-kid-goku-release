import {execFileSync, spawnSync} from 'node:child_process';
import {cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {writeStamp} from './build-stamp.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const blender = process.env.BLENDER ?? '/Applications/Blender 5.3.app/Contents/MacOS/Blender';
const original = join(root, 'private', 'downloads', 'template', 'char-select-template-main', 'actors', 'template.blend');

const template = join(dirname(original), 'template-5.blend');
const out = join(root, 'private', 'build', 'actors');
const actors = join(root, 'mod', 'kid-goku', 'actors');

const checkEnv = join(root, 'private', 'check.env');
const envPython = existsSync(checkEnv) && readFileSync(checkEnv, 'utf8').split('\n').find(l => l.startsWith('PYTHON='));
const py = process.env.PYTHON || (envPython ? envPython.slice(7).replace(/^"(.*)"$/, '$1') : 'python3');
try {
  execFileSync(py, ['-c', 'import PIL, numpy, shapely, resvg_py'], {stdio: 'pipe'});
} catch {
  console.error(`build: ${py} can't import Pillow, numpy, shapely and resvg-py. Make a venv of scripts/requirements.txt and set PYTHON= in private/check.env.`);
  process.exit(1);
}
if (!existsSync(template)) {
  const made = spawnSync(blender, ['-b', '--factory-startup', '--python', join(root, 'scripts', 'blender', 'convert_template.py'), '--', original, template], {encoding: 'utf8'});
  if (!existsSync(template)) throw new Error(`couldn't convert the template:\n${made.stdout}${made.stderr}`);
}
rmSync(out, {recursive: true, force: true});
mkdirSync(out, {recursive: true});
const run = args => {

  const script = args.indexOf('--python');
  const ran = spawnSync(blender, ['-b', ...args.slice(0, script), '--addons', 'fast64', ...args.slice(script)],
    {encoding: 'utf8', maxBuffer: 64 << 20, timeout: 300000, env: {...process.env, GOKU_OUTLINE: '1'}});
  if (ran.error) throw ran.error;
  const log = ran.stdout + ran.stderr;
  for (const line of log.split('\n')) if (/^(built Mario Mesh|built goku_|arms in|Kid Goku|fit errors|extracted|exported|joint|reduced|wrote)|Traceback|Error: (?!Not freed|Unable to pack)/.test(line)) console.log(line);

  if (log.includes('Traceback (most recent call last)')) throw new Error(`Blender failed:\n${log.slice(log.indexOf('Traceback (most recent call last)'))}`);
};

const b3 = join(root, 'private', 'rips', 'kid-goku-b3', 'Kid Goku');
const rip = join(root, 'private', 'rips', 'kid-goku', 'chara011_1p.gltf');
if (process.env.GOKU_BASE === 'b3' && existsSync(b3)) {
  const data = join(root, 'private', 'build', 'b3.json');
  run(['--factory-startup', '--python', join(root, 'scripts', 'blender', 'obj_extract.py'), '--',
    join(b3, 'Kid_Goku_Budokai_3.obj'), data]);
  for (const [actor, dir] of [['goku', b3], ['goku_turtle', join(b3, 'Kid Goku_Alt')]]) {
    const tex = join(root, 'private', 'build', `tex-${actor}`);
    execFileSync(py, [join(root, 'scripts', 'b3_textures.py'), dir, tex], {stdio: 'inherit'});
    run([template, '--python', join(root, 'scripts', 'blender', 'b3.py'), '--', data, tex, actor, out,
      join(root, 'private', 'build', 'goku-rig.json')]);
  }
} else if (existsSync(rip)) {
  const data = join(root, 'private', 'build', 'rip.json');
  run(['--factory-startup', '--python', join(root, 'scripts', 'blender', 'rip_extract.py'), '--', rip, data]);
  const tex = join(root, 'private', 'build', 'n64tex');
  execFileSync(py, [join(root, 'scripts', 'rip_textures.py'), dirname(rip), tex], {stdio: 'inherit'});
  run([template, '--python', join(root, 'scripts', 'blender', 'bt3.py'), '--', data, out,
    join(root, 'private', 'build', 'goku-rig.json'), tex]);

  execFileSync(py, [join(root, 'scripts', 'faces.py'), join(root, 'private', 'build', 'goku-face.json'),
    join(root, 'art', 'faces'), join(out, 'goku')], {stdio: 'inherit'});

  execFileSync(py, [join(root, 'scripts', 'face_shapes.py'), join(out, 'goku', 'model.inc.c')], {stdio: 'inherit'});

  execFileSync(py, [join(root, 'scripts', 'blend_nodes.py'), join(out, 'goku', 'geo.inc.c')], {stdio: 'inherit'});
} else {
  run([template, '--python', join(root, 'scripts', 'blender', 'goku.py'), '--', out, join(root, 'private', 'build', 'goku.blend')]);
}
run(['--python', join(root, 'scripts', 'blender', 'props.py'), '--', out]);

const checkout = dirname(execFileSync('git', ['-C', root, 'rev-parse', '--path-format=absolute', '--git-common-dir'], {encoding: 'utf8'}).trim());
const constants = process.env.SM64COOPDX_CONSTANTS ??
  join(checkout, '..', 'sm64coopdx-web', 'upstream', 'autogen', 'lua_definitions', 'constants.lua');
if (!existsSync(constants)) throw new Error(`no sm64coopdx constants at ${constants}: set SM64COOPDX_CONSTANTS`);
run(['--factory-startup', '--python', join(root, 'scripts', 'blender', 'anims.py'), '--',
  join(root, 'art', 'mario-anim-timing.json'), join(root, 'mod', 'kid-goku', 'anims-data.lua'), constants]);

rmSync(actors, {recursive: true, force: true});
mkdirSync(actors, {recursive: true});
for (const name of readdirSync(out)) cpSync(join(out, name), join(actors, name), {recursive: true});
console.log('actors:', readdirSync(actors).join(', '));
writeStamp(root);
