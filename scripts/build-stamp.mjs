import {createHash} from 'node:crypto';
import {existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';

const PY = ['face_shapes', 'blend_nodes', 'faces', 'head_light', 'ear', 'rip_textures', 'textures'];

function hash(paths) {
  const h = createHash('sha256');
  for (const p of paths) if (existsSync(p)) { h.update(p.slice(p.lastIndexOf('/') + 1)); h.update(readFileSync(p)); }
  return h.digest('hex');
}

export function scriptsHash(root) {
  const blender = join(root, 'scripts', 'blender');
  return hash([...readdirSync(blender).filter(f => f.endsWith('.py')).sort().map(f => join(blender, f)),
    ...PY.map(n => join(root, 'scripts', `${n}.py`)), join(root, 'scripts', 'build.mjs')]);
}

export function artHash(root) {
  const art = join(root, 'art', 'faces');
  return hash(readdirSync(art).filter(f => f.endsWith('.svg')).sort().map(f => join(art, f)));
}

const stampPath = root => join(root, 'private', 'build', 'stamp.json');

export function writeStamp(root) {
  mkdirSync(join(root, 'private', 'build'), {recursive: true});
  writeFileSync(stampPath(root), JSON.stringify({scripts: scriptsHash(root), art: artHash(root)}) + '\n');
}

export function stampArt(root) {
  const stamp = JSON.parse(readFileSync(stampPath(root), 'utf8'));
  writeFileSync(stampPath(root), JSON.stringify({...stamp, art: artHash(root)}) + '\n');
}

export function staleReason(root) {
  if (!existsSync(stampPath(root))) return 'nothing has been built here yet';
  const stamp = JSON.parse(readFileSync(stampPath(root), 'utf8'));
  if (stamp.scripts !== scriptsHash(root)) return 'the model scripts changed after the last good build';
  if (stamp.art !== artHash(root)) return 'the faces changed after they were last painted';
  return null;
}

export function refuseStale(root, argv) {
  const why = staleReason(root);
  if (!why || argv.includes('--stale-ok')) return;
  console.log(`FAIL stale model: ${why}. Run node scripts/build.mjs, or pass --stale-ok if the change doesn't touch the model.`);
  process.exit(1);
}
