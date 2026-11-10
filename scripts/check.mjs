import {execFileSync, spawn} from 'node:child_process';
import {cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {refuseStale} from './build-stamp.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
refuseStale(root, process.argv);
const env = Object.fromEntries(readFileSync(join(root, 'private', 'check.env'), 'utf8').split('\n')
  .filter(l => /^\w+=/.test(l)).map(l => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).replace(/^"(.*)"$/, '$1')]));
const arg = (name, fallback) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : fallback; };
const seconds = +arg('--seconds', 120);
const filmCase = arg('--case', process.argv.includes('--showcase') ? 'showcase' : null);
const showcase = filmCase !== null;
const capture = showcase || process.argv.includes('--capture');
const fast = !capture && env.COOPDX_FAST_BIN && existsSync(env.COOPDX_FAST_BIN);
const bin = capture ? env.FILM_BIN : fast ? env.COOPDX_FAST_BIN : env.COOPDX_BIN;
const frames = join(root, 'private', 'capture');
if (capture) { rmSync(frames, {recursive: true, force: true}); mkdirSync(frames, {recursive: true}); }

const home = mkdtempSync(join(tmpdir(), 'goku-check-'));
mkdirSync(join(home, 'mods'), {recursive: true});
mkdirSync(join(home, 'sav'), {recursive: true});
cpSync(env.SM64_ROM, join(home, 'baserom.us.z64'));
const mods = {'character-select-coop': env.CHARACTER_SELECT, 'kid-goku': join(root, 'mod', 'kid-goku'),
  'kid-goku-check': join(root, 'test', filmCase ?? 'in-game')};

const STAND_IN = `
audio_sample_load = function(name) local h = {filepath = name, _pointer = true}; h[1] = h; return h end
audio_stream_load = audio_sample_load
`;
const LOG_SAMPLES = `
audio_sample_play = function(h, pos, vol)
  local gain, pan = 1, 0
  if film_sound_level and pos then gain, pan = film_sound_level(pos.x, pos.y, pos.z) end
  print('[GOKUTEST] AUDIO ' .. get_global_timer() .. ' ' .. h.filepath .. ' ' .. (vol or 1) * gain .. ' ' .. pan)
end
`;
const MUTE = "for name, f in pairs(_G) do if type(f) == 'function' and (name:find('^audio_sample_') or name:find('^audio_stream_')) then _G[name] = function() end end end\n" +
  STAND_IN + (filmCase ? LOG_SAMPLES : '');
for (const [folder, from] of Object.entries(mods)) {
  cpSync(from, join(home, 'mods', folder), {recursive: true});
  writeFileSync(join(home, 'mods', folder, '0-silent.lua'), MUTE);
}

const song = join(home, 'mods', 'kid-goku', 'sound', 'goku_wing_song.ogg');
if (!existsSync(song)) {
  mkdirSync(dirname(song), {recursive: true});
  writeFileSync(song, '');
}

if (process.argv.includes('--key-lines')) {
  const PARTS = ['Butt', 'Torso', 'Head', 'Arm', 'Forearm', 'Hand', 'Thigh', 'Leg', 'Shoe', 'Pole'];
  const actors = join(home, 'mods', 'kid-goku', 'actors');
  for (const actor of readdirSync(actors)) {
    const model = join(actors, actor, 'model.inc.c');
    if (!existsSync(model)) continue;
    const keyed = readFileSync(model, 'utf8').split(/^(?=Vtx )/m).map(block => {
      const name = /^Vtx (\w+)/.exec(block)?.[1] ?? '';

      const chin = /Head.*_vtx_[1-9]/.test(name);
      const at = actor === 'goku_tail' ? 10 : chin ? 11 : PARTS.findIndex(part => name.includes(`_${part}`));
      return block.replace(/\{(10, 10, 14|18, 10, 8), 255\}/g, `{255, ${at < 0 ? 55 : at * 5}, 255, 255}`);
    }).join('');
    writeFileSync(model, keyed);
  }
}
writeFileSync(join(home, 'mods', 'kid-goku-check', '0-capture.lua'), `GOKU_CAPTURE = ${capture}\nGOKU_SHOTS = ${JSON.stringify(arg('--shots', ''))}\n`);
writeFileSync(join(home, 'sm64config.txt'), 'skip_intro true\nmaster_volume 0\nmusic_volume 0\nsfx_volume 0\nenv_volume 0\n' +
  Object.keys(mods).map(m => `enable-mod: ${m}\n`).join(''));

const args = [...(capture ? ['--film-out', frames, '--film-size', arg('--film-size', '640x480')] : ['--headless']), '--server', '7777', '--savepath', home, '--skip-update-check', '--no-discord', '--console',
  '--playername', 'Goku'];
const game = spawn(bin, args, {cwd: dirname(bin), env: {...process.env, SDL_AUDIODRIVER: 'dummy',
  SDL_MAC_BACKGROUND_APP: '1', ...(fast ? {SM64COOPDX_CLOCK_SPEED: '10'} : {})}});
let failed = 0, done = false, tail = '', log = '';
const clips = {};
const onData = chunk => {
  log += chunk.toString();
  const text = tail + chunk.toString();
  const lines = text.split('\n');
  tail = lines.pop();
  for (const line of lines) {
    if (line.includes('[GOKUTEST]') && !line.includes('FRAME')) console.log(line.trim());
    else if (/\[LUA\].*(error|attempt)|stack traceback|DynOS.*(error|fail)/i.test(line)) { console.log(line.trim()); failed++; }
    if (line.includes('[GOKUTEST] FAIL')) failed++;
    if (line.includes('[GOKUTEST] DONE')) { done = true; game.kill('SIGKILL'); }
    const mark = /\[GOKUTEST\] (CLIP|CLIPEND) (\S+) (\d+)/.exec(line);
    if (mark) (clips[mark[2]] ??= {})[mark[1] === 'CLIP' ? 'from' : 'to'] = +mark[3];
  }
};
game.stdout.on('data', onData);
game.stderr.on('data', onData);

function cut() {
  const files = readdirSync(frames).filter(f => f.endsWith('.ppm')).sort();
  const dir = join(root, 'private', 'clips');
  mkdirSync(dir, {recursive: true});
  for (const [name, {from, to}] of Object.entries(clips)) {
    if (from === undefined || to === undefined) continue;
    const list = join(frames, `${name}.txt`);
    writeFileSync(list, files.slice(from, to).map(f => `file '${join(frames, f)}'\nduration 0.0333333\n`).join(''));
    if (process.argv.includes('--no-clips')) continue;
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-r', '30',
      '-vf', 'scale=960:720:flags=neighbor', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-an',
      join(dir, `kid-goku-${name}.mp4`)]);
    console.log(`clip ${name}: ${to - from} frames`);
  }
}
const timer = setTimeout(() => game.kill('SIGKILL'), seconds * 1000);
game.on('exit', () => {
  clearTimeout(timer);
  if (!done) { console.log('timed out before DONE'); failed++; }
  if (showcase) cut();
  writeFileSync(join(root, 'private', 'last-game-log.txt'), log);
  if (process.argv.includes('--keep')) console.log(`kept ${home}`);
  process.exit(failed ? 1 : 0);
});
