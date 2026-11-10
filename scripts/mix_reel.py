"""Turn the last filmed case into one video with its sound: the game's own (private/capture/audio.s16) with every sample
the mods played laid in where the log says it started. Run after node scripts/check.mjs --showcase (needs ffmpeg, numpy
and soundfile). The mix is rebuilt from what the game asked to play; it isn't a recording of the speaker.

Usage: python3 scripts/mix_reel.py OUT.mp4 [--clips a,b,c] [--film-gain DB]
"""
import argparse
from pathlib import Path
import re
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RATE = 32000


def at(frame):
    """The sample a picture starts on. A game frame is 1066 and two-thirds samples."""
    return frame * RATE // 30


def sample(name, folders):
    for folder in folders:
        path = folder / name
        if path.exists():
            pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ar", str(RATE), "-ac", "1", "-f", "f32le",
                                  "pipe:1"], capture_output=True, check=True).stdout
            return np.frombuffer(pcm, dtype=np.float32)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--clips", default="", help="only these clips, in this order")
    parser.add_argument("--film-gain", type=float, default=-6, help="dB on the game's own sound under the voice")
    args = parser.parse_args()

    log = (ROOT / "private/last-game-log.txt").read_text()
    frames_dir = ROOT / "private/capture"
    frames = sorted(frames_dir.glob("*.ppm"))
    raw = np.fromfile(frames_dir / "audio.s16", dtype=np.int16).reshape(-1, 2).astype(np.float32) / 32768
    mix = np.zeros((at(len(frames)), 2), dtype=np.float32)
    n = min(len(raw), len(mix))
    mix[:n] = raw[:n] * 10 ** (args.film_gain / 20)

    rolls = [(int(t), int(f)) for t, f in re.findall(r"\[GOKUTEST\] ROLL (\d+) (\d+)", log)]
    marks = {name: [int(a), None] for name, a in re.findall(r"\[GOKUTEST\] CLIP (\S+) (\d+)", log)}
    for name, b in re.findall(r"\[GOKUTEST\] CLIPEND (\S+) (\d+)", log):
        marks[name][1] = int(b)
    folders = [ROOT / "mod/kid-goku/sound"]
    played = 0
    for t, name, volume, pan in re.findall(r"\[GOKUTEST\] AUDIO (\d+) (\S+) ([\d.e-]+) ([-\d.e]+)", log):
        t = int(t)
        roll = next(((rt, rf) for rt, rf in reversed(rolls) if rt <= t), None)
        if roll is None:
            continue
        frame = roll[1] + t - roll[0]
        pcm = sample(name, folders)
        if pcm is None or not 0 <= frame < len(frames):
            continue
        start = at(frame)
        pcm = pcm[:len(mix) - start]
        left, right = np.sqrt((1 - float(pan)) / 2), np.sqrt((1 + float(pan)) / 2)
        mix[start:start + len(pcm), 0] += pcm * float(volume) * left * np.sqrt(2)
        mix[start:start + len(pcm), 1] += pcm * float(volume) * right * np.sqrt(2)
        played += 1
    peak = max(1e-6, float(np.abs(mix).max()))
    mix *= min(1, 0.84 / peak)

    order = [c for c in args.clips.split(",") if c] or list(marks)
    keep = [(marks[c][0], marks[c][1]) for c in order]
    wav = frames_dir / "mix.f32"
    np.concatenate([mix[at(a):at(b)] for a, b in keep]).tofile(wav)
    listing = frames_dir / "reel.txt"
    listing.write_text("".join(f"file '{frames[i]}'\nduration 0.0333333\n" for a, b in keep for i in range(a, b)))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-f", "f32le", "-ar",
                    str(RATE), "-ac", "2", "-i", str(wav), "-r", "30", "-vf", "format=yuv420p", "-c:v", "libx264",
                    "-crf", "16", "-preset", "medium", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest",
                    str(args.out)], check=True)
    print(f"{args.out}: {sum(b - a for a, b in keep)} frames, {played} samples laid in")


if __name__ == "__main__":
    main()
