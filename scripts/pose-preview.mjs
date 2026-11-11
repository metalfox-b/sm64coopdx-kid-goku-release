import {execFileSync} from 'node:child_process';
import {existsSync, mkdirSync, readFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const blender = process.env.BLENDER ?? '/Applications/Blender 5.3.app/Contents/MacOS/Blender';
const model = join(root, 'private', 'build', 'goku.blend');
const args = process.argv.slice(2);
const arg = (name, fallback) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : fallback; };
const SWITCHES = ['--turntable', '--show-failing'];
const [motion, at] = args.filter((a, i) => !a.startsWith('--') && !(args[i - 1]?.startsWith('--') && !SWITCHES.includes(args[i - 1])));
if (!motion || at === undefined || Number.isNaN(+at)) {
  console.error('usage: node scripts/pose-preview.mjs MOTION|FIT.json T [--face PASSED] [--frame PICTURE] [--out FILE.png] [--turntable] [--show-failing]');
  process.exit(1);
}
if (!existsSync(model)) {
  console.error('pose-preview: no private/build/goku.blend; run node scripts/build.mjs first');
  process.exit(1);
}

const fitted = motion.endsWith('.json');
const hand = 'fist';
const out = resolve(arg('--out', join(root, 'private', 'pose-preview', `${fitted ? 'fit' : motion}-${at}.png`)));
mkdirSync(dirname(out), {recursive: true});
const frame = arg('--frame', null);

const face = arg('--face', 'relaxed');
const turntable = args.includes('--turntable') ? out.replace(/\.png$/, '') + '-turntable' : null;
const env = {...process.env, ...(turntable ? {POSE_PREVIEW_TURNTABLE: turntable} : {}),
  ...(args.includes('--show-failing') ? {POSE_PREVIEW_SHOW_FAILING: '1'} : {})};
let log;
try {
  log = execFileSync(blender, ['-b', model, '--addons', 'fast64', '--python', join(root, 'scripts', 'blender', 'pose_preview.py'), '--',
    fitted ? resolve(motion) : motion, String(at), out, hand, face, ...(frame ? [resolve(frame)] : [])], {encoding: 'utf8', maxBuffer: 64 << 20, timeout: 300000, env});
} catch (err) {
  log = String(err.stdout ?? '') + String(err.stderr ?? '');
}
if (log.includes('Traceback (most recent call last)')) {
  console.error(log.slice(log.indexOf('Traceback (most recent call last)')));
  process.exit(1);
}
const done = log.split('\n').find(line => line.startsWith('pose preview:') || line.startsWith('pose_preview:'));
for (const line of log.split('\n')) if (line.startsWith('pose stamp:')) console.log(line);
console.log(done ?? log.slice(-2000));
if (!done?.startsWith('pose preview:')) process.exit(1);
if (fitted) {
  const checkEnv = join(root, 'private', 'check.env');
  const line = existsSync(checkEnv) && readFileSync(checkEnv, 'utf8').split('\n').find(l => l.startsWith('PYTHON='));
  const py = process.env.PYTHON || (line ? line.slice(7) : 'python3');
  console.log(execFileSync(py, [join(root, 'scripts', 'draw_fit.py'), resolve(motion), String(at), out.replace(/\.png$/, '-skeleton.png')], {encoding: 'utf8'}).trim());
}
if (turntable) {
  const still = fitted ? JSON.parse(readFileSync(resolve(motion), 'utf8')).image : frame && resolve(frame);
  const video = `${turntable}.mp4`;
  const inputs = ['-f', 'lavfi', '-i', 'color=c=0x202226:s=480x480:r=8', '-framerate', '8', '-stream_loop', '2', '-i', join(turntable, 'v-t%02d.png')];
  const graph = still ? '[0][1]overlay=shortest=1[t];[2]scale=-2:480[f];[t][f]hstack,format=yuv420p' : '[0][1]overlay=shortest=1,format=yuv420p';
  execFileSync('ffmpeg', ['-loglevel', 'error', '-y', ...inputs, ...(still ? ['-i', still] : []), '-filter_complex', graph,
    '-c:v', 'libx264', '-crf', '20', '-movflags', '+faststart', video]);
  console.log(`turntable: ${video} (and from above: ${join(turntable, 'v-top.png')})`);
}
