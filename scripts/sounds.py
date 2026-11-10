"""Build the local Japanese Kid Goku sounds from Budokai Tenkaichi 3 (US PS2, SLUS-21678)."""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory

import soundfile

ROOT = Path(__file__).resolve().parents[1]
RIPS = ROOT / "private/rips/tenkaichi3-jp"
SOUND = ROOT / "mod/kid-goku/sound"

VOICES = {
    "start": (33893,), "lets_go": (33953,), "star": (33918,),
    "rock": (33964, .955, 1.28), "scissors": (33964, 1.410, 1.705), "paper": (33964, 1.920, 2.30),
    "jump1": (33917,), "jump2": (33939,), "jump3": (33944,), "double_jump": (33940,),
    "triple_jump1": (33932,), "triple_jump2": (33921,), "long_jump": (33923,),
    "bonk": (33945,), "ledge": (33942,), "land": (33937,), "hurt": (33928,), "falling": (33922,),
    "lift": (33934,), "throw": (33920,), "dying": (33947,), "burned": (33946,), "game_over": (33936,),
    "ka": (33961, .02, .135, .6), "me": (33961, .135, .225, .6), "ha2": (33961, .205, .345, .6),
    "me2": (33961, .37, .505, .6), "ha": (33961, .505, .87, .85),
}
EFFECTS = {"kame_impact": (28, 0, 1.18)}
HASHES = {
    "33961.adx": "0dcc8789192f787c1732f743d2a9a532114677b7fd5c382546918ceed8b0e2a6",
    "SE_Battle.pak": "068dc1c37f1502b40eee5fbe7322cb81f7ab255abdb03026952c1653a533982d",
}


def afs_entry(disc, base, index):
    disc.seek(base)
    magic, count = struct.unpack("<4sI", disc.read(8))
    if magic != b"AFS\0" or index >= count:
        raise ValueError("Expected the US retail PS2 disc with both language banks")
    disc.seek(base + 8 + index * 8)
    offset, size = struct.unpack("<II", disc.read(8))
    disc.seek(base + offset)
    data = disc.read(size)
    if len(data) != size:
        raise ValueError("Incomplete disc image")
    return data


def check_inputs(inputs):
    for name, expected in HASHES.items():
        if hashlib.sha256(inputs[name]).hexdigest() != expected:
            raise ValueError(f"{name} differs from the Japanese Kid Goku / US retail battle bank")
    for name, data in inputs.items():
        if name.endswith(".adx") and not data.startswith(b"\x80\x00"):
            raise ValueError(f"{name} is not an ADX recording")


def effect_sample(bank, slot):
    _, body, header, end = struct.unpack_from("<4I", bank)
    table = bank.index(b"IECSigaV", header, end)
    count = struct.unpack_from("<I", bank, table + 12)[0] + 1
    offsets = struct.unpack_from(f"<{count}I", bank, table + 16)
    start, rate = struct.unpack_from("<IH", bank, table + offsets[slot])
    stop = struct.unpack_from("<I", bank, table + offsets[slot + 1])[0] if slot + 1 < count else header - body
    samples = bank[body + start:body + stop]
    return struct.pack(">4s5I", b"VAGp", 32, 0, len(samples), rate, 0) + bytes(24) + samples


def encode(data, fmt, path, trim, gain):
    start, stop, tempo = (list(trim) + [None] * 3)[:3]
    filters = []
    if stop is not None:
        filters.extend([f"atrim=start={start}:end={stop}", "asetpts=PTS-STARTPTS"])
    if tempo is not None:
        filters.append(f"atempo={tempo}")
    filters += ["afade=t=in:d=0.003", "areverse", "afade=t=in:d=0.012", "areverse", f"volume={gain}dB"]
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", fmt, "-i", "pipe:0",
                          "-af", ",".join(filters), "-ac", "1", "-ar", "32000", "-f", "s16le", "pipe:1"],
                         input=data, capture_output=True, check=True).stdout
    with soundfile.SoundFile(path, mode="w", samplerate=32000, channels=1, format="OGG", subtype="VORBIS",
                             compression_level=0.6) as out:
        out.buffer_write(pcm, dtype="int16")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disc", type=Path, help="read just these sound entries from a local US PS2 ISO")
    args = parser.parse_args()
    ids = sorted({cue[0] for cue in VOICES.values()})
    if args.disc:
        with args.disc.open("rb") as disc:
            inputs = {f"{i}.adx": afs_entry(disc, 1466093568, i) for i in ids}
            inputs["SE_Battle.pak"] = afs_entry(disc, 4075520, 329)
        check_inputs(inputs)
        RIPS.mkdir(exist_ok=True, parents=True)
        for name, data in inputs.items():
            (RIPS / name).write_bytes(data)
    else:
        inputs = {name: (RIPS / name).read_bytes() for name in [*(f"{i}.adx" for i in ids), "SE_Battle.pak"]}
        check_inputs(inputs)

    SOUND.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=SOUND) as scratch:
        dest = Path(scratch)
        for name, (index, *trim) in VOICES.items():
            encode(inputs[f"{index}.adx"], "adx", dest / f"goku_{name}.ogg", trim, -5)
        for name, (slot, *trim) in EFFECTS.items():
            data = effect_sample(inputs["SE_Battle.pak"], slot)
            encode(data, "vag", dest / f"goku_{name}.ogg", trim, -6)
        for cue in dest.iterdir():
            cue.replace(SOUND / cue.name)
    print(f"Built {len(VOICES) + len(EFFECTS)} Japanese Kid Goku voice and battle clips in {SOUND}")


if __name__ == "__main__":
    main()
