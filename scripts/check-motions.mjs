import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const sha = text => createHash('sha256').update(text).digest('hex');
const listOf = root => join(root, 'art', 'motions-kept.json');

export function clipsOf(root, motion) {
  const lines = readFileSync(join(root, 'mod', 'kid-goku', 'anims-data.lua'), 'utf8').split('\n');
  const clips = {};
  const name = new RegExp(`^smlua_anim_util_register_animation\\('(goku_${motion}(?:_\\d+)?)'`);
  lines.forEach((line, i) => {
    const m = name.exec(line);
    if (!m) return;
    let start = i - 1;
    while (start > 0 && !lines[start].startsWith('do local v')) start--;
    if (lines[start]?.startsWith('do local v')) clips[m[1]] = sha(lines.slice(start, i + 1).join('\n'));
  });
  return clips;
}

export function problems(root) {
  const kept = JSON.parse(readFileSync(listOf(root), 'utf8')).motions;
  const found = [];
  for (const [motion, entry] of Object.entries(kept)) {
    const now = clipsOf(root, motion);
    if (!Object.keys(now).length) { found.push(`${motion}: kept, and its clips are gone`); continue; }
    for (const [clip, hash] of Object.entries(entry.clips)) {
      if (now[clip] === undefined) found.push(`${motion}: kept, and its clip ${clip} is gone`);
      else if (now[clip] !== hash) found.push(`${motion}: ${clip} isn't what Metal Fox kept ("${entry.said}")`);
    }
  }
  return found;
}

function main() {
  const root = join(dirname(fileURLToPath(import.meta.url)), '..');
  const args = process.argv.slice(2);
  const arg = name => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
  const list = JSON.parse(readFileSync(listOf(root), 'utf8'));
  const said = arg('--said');
  for (const flag of ['--keep', '--unlock']) {
    const motion = arg(flag);
    if (!motion) continue;
    if (!said) { console.error(`${flag} needs Metal Fox's words: --said "…"`); process.exit(1); }
    if (flag === '--keep') {
      const clips = clipsOf(root, motion);
      if (!Object.keys(clips).length) { console.error(`no clips of ${motion} in anims-data.lua`); process.exit(1); }
      list.motions[motion] = {said, clips};
    } else {
      if (!list.motions[motion]) { console.error(`${motion} isn't kept`); process.exit(1); }
      delete list.motions[motion];
      list.unlocked = [...(list.unlocked ?? []), {motion, said}];
    }
    writeFileSync(listOf(root), JSON.stringify(list, null, 1) + '\n');
    console.log(`${flag === '--keep' ? 'kept' : 'unlocked'} ${motion}`);
    return;
  }
  const found = problems(root);
  for (const f of found) console.error(f);
  if (found.length) process.exit(1);
  console.log('motions hold');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
