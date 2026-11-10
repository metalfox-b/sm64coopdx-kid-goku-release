import {readFileSync} from 'node:fs';
import {homedir} from 'node:os';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {refuseStale} from './build-stamp.mjs';

const {runGame, luaDiagnostics} = await import(join(homedir(), 'Developer', 'SM64 Coop DX Dev Tools', 'scripts', 'lib', 'game.mjs'));
const root = join(dirname(fileURLToPath(import.meta.url)), '..');
refuseStale(root, process.argv);
const env = Object.fromEntries(readFileSync(join(root, 'private', 'check.env'), 'utf8').split('\n')
  .filter(l => /^\w+=/.test(l)).map(l => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).replace(/^"(.*)"$/, '$1')]));

const port = 20847;
const base = {rom: env.SM64_ROM, bin: env.COOPDX_BIN, port, seconds: 110,
  mods: [{dir: env.CHARACTER_SELECT}, {dir: join(root, 'mod', 'kid-goku')}, {dir: join(root, 'test', 'pair')}]};
const said = [];
const listen = who => (line, stop) => {
  if (!line.includes('[PAIR]')) return;
  console.log(who, line.trim());
  said.push(`${who} ${line}`);
  if (line.includes('host done') || line.includes('client done')) stop();
};
const host = runGame({...base, name: 'Host', onLine: listen('host')});
await new Promise(resolve => setTimeout(resolve, 1500));
const client = runGame({...base, name: 'Client', client: ['127.0.0.1', port], onLine: listen('client')});
const results = await Promise.all([host, client]);

let failed = 0;
for (const want of ['host [PAIR] tails on their players true', 'client [PAIR] tails on their players true',
    'host [PAIR] remote charge', 'host [PAIR] remote beam', 'host [PAIR] remote cleanup', 'client [PAIR] client beam true',
  'client [PAIR] client miss true', 'client [PAIR] client impact true', 'host [PAIR] remote impact', 'client [PAIR] client stomp true', 'client [PAIR] client stomp clip true', 'client [PAIR] client no stomp without an enemy true',
  'host [PAIR] remote stomp', 'client [PAIR] client rides the Nimbus true', 'host [PAIR] remote rides one cloud true',
  'host [PAIR] remote called once true', 'host [PAIR] remote keeps a cloud after a false landing true',
  'host [PAIR] remote has a cloud when first seen riding true', 'client [PAIR] client rides it again true',
  'host [PAIR] remote calls once after an early end true']) {
  if (!said.some(line => line.includes(want))) { console.log('FAIL', want); failed++; }
}
for (const {log, speaker} of results) {
  for (const line of luaDiagnostics(log)) { console.log(line); failed++; }
  if (speaker.length) { console.log('speaker held', speaker[0]); failed++; }
}
console.log(failed ? `${failed} failed` : 'pair passed');
process.exit(failed ? 1 : 0);
