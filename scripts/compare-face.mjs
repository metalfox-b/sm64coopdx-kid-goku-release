import {execFileSync} from 'node:child_process';
import {copyFileSync, existsSync, mkdirSync, readFileSync, rmSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {scriptsHash, stampArt} from './build-stamp.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const name = process.argv[2];
if (!name || name.startsWith('--')) { console.log('usage: node scripts/compare-face.mjs NAME [--front] [--frame FILE]'); process.exit(1); }
const arg = flag => { const i = process.argv.indexOf(flag); return i > 0 ? process.argv[i + 1] : undefined; };
const python = process.env.PYTHON ?? 'python3';
const out = join(root, 'private', 'compare', name);
mkdirSync(out, {recursive: true});
const run = (cmd, args) => execFileSync(cmd, args, {stdio: 'inherit', cwd: root});

run(python, [join(root, 'scripts', 'trace_faces.py'), name]);
run(python, [join(root, 'scripts', 'compare_face.py'), 'front', name, out]);
if (process.argv.includes('--front')) process.exit(0);

const stamp = join(root, 'private', 'build', 'stamp.json');
if (!existsSync(stamp) || JSON.parse(readFileSync(stamp, 'utf8')).scripts !== scriptsHash(root)) {
  console.log('FAIL the model scripts changed after the last good build: run node scripts/build.mjs first.');
  process.exit(1);
}
const built = join(root, 'private', 'build', 'actors', 'goku');
run(python, [join(root, 'scripts', 'faces.py'), join(root, 'private', 'build', 'goku-face.json'), join(root, 'art', 'faces'), built]);
copyFileSync(join(built, `goku_face_${name}.ci4.png`), join(root, 'mod', 'kid-goku', 'actors', 'goku', `goku_face_${name}.ci4.png`));
stampArt(root);
run('node', [join(root, 'scripts', 'check.mjs'), '--case', 'review', '--shots', 'faces-close,faces-quarter', '--film-size', '1920x1440', '--seconds', '300', '--no-clips']);

const common = resolve(root, execFileSync('git', ['rev-parse', '--git-common-dir'], {cwd: root, encoding: 'utf8'}).trim());
const frames = [join(root, 'private', 'reference', 'anime-faces'), join(dirname(common), 'private', 'reference', 'anime-faces')].find(existsSync);
if (!frames) { console.log('FAIL no private/reference/anime-faces here or in the main checkout'); process.exit(1); }
run(python, [join(root, 'scripts', 'compare_face.py'), 'sheets', name, join(root, 'private', 'capture'), frames, out, arg('--frame') ?? '', ...(arg('--box') ? [arg('--box')] : [])]);
rmSync(join(root, 'private', 'capture'), {recursive: true, force: true});

console.log('\nMeasured against his passed faces:');
try { run(python, [join(root, 'scripts', 'judge_face.py'), 'judge', join(out, 'crop.png')]); } catch { console.log('(faults above: fix them before anyone sees this)'); }
console.log('\nWhat Metal Fox has turned down:');
for (const {idea, said} of JSON.parse(readFileSync(join(root, 'art', 'faces', 'rejected.json'), 'utf8')).ideas) console.log(`  ${idea}: "${said}"`);
