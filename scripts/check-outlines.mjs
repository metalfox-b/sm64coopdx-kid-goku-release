import {execFileSync} from 'node:child_process';
import {existsSync, mkdirSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const arg = (name, fallback) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : fallback; };
const out = arg('--out', join(root, 'private', 'outlines'));
const python = process.env.PYTHON ?? 'python3';
const shots = ['stand', 'low', 'tiptoe', 'walk', 'run', 'jump', 'combo', 'kame'].map(s => `lines-${s}`).join(',');
const baseline = join(root, 'test', 'outlines-baseline.json');
const room = 1.1;

execFileSync('node', [join(root, 'scripts', 'check.mjs'), '--case', 'review', '--shots', shots, '--film-size', '1920x1440',
  '--seconds', '500', '--key-lines', '--no-clips'], {stdio: 'inherit'});
rmSync(out, {recursive: true, force: true});
mkdirSync(out, {recursive: true});
execFileSync(python, [join(root, 'scripts', 'outlines.py'), join(root, 'private', 'capture'), out, shots, '4'], {stdio: 'inherit'});
rmSync(join(root, 'private', 'capture'), {recursive: true, force: true});
execFileSync('node', [join(root, 'scripts', 'check.mjs'), '--case', 'review', '--shots', 'lines-stand', '--film-size', '1920x1440', '--seconds', '200', '--no-clips'], {stdio: 'inherit'});
execFileSync(python, [join(root, 'scripts', 'outlines.py'), 'round', join(root, 'private', 'capture'), out], {stdio: 'inherit'});
rmSync(join(root, 'private', 'capture'), {recursive: true, force: true});

const now = JSON.parse(readFileSync(join(out, 'report.json'), 'utf8')).all;
if (process.argv.includes('--update') || !existsSync(baseline)) {
  writeFileSync(baseline, JSON.stringify(now, null, 2) + '\n');
  console.log('baseline written');
  process.exit(0);
}
const was = JSON.parse(readFileSync(baseline, 'utf8'));
const worse = Object.keys(now).filter(k => now[k] > was[k] * room);
for (const k of Object.keys(now)) console.log(`${k}: ${now[k]} (baseline ${was[k]})`);
if (worse.length) { console.log(`FAIL worse: ${worse.join(', ')}; look at ${out}`); process.exit(1); }
console.log('outlines hold');
