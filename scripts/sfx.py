"""Trim and level the battle sound effects and voice clips Metal Fox supplied (private/sfx/ and private/voice/, out of Git) into
mod/kid-goku/sound/.

Usage: python3 scripts/sfx.py

The Kamehameha clip is a rising energy charge, 0.25 to 6.4 s, then the blast and its shout from 6.46 s. A charge can be let go
at any moment and held past full, and a sample can't fade out once it's playing, so the rise is squeezed to the three seconds
of a full charge and cut into steps that overlap. Stop calling steps and it ends within one.
"""
from pathlib import Path
import subprocess

import numpy as np
import soundfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "private/sfx"
VOICE = ROOT / "private/voice"
SOUND = ROOT / "mod/kid-goku/sound"
RATE = 32000

PUNCH = "Dragon-Ball-Z-Punch-Sound-Effect-N_9.mp3"
HEAVY_PUNCH = "Dragon_Ball_Z_Heavy_Punch.mp3"
HEAVY_KICK = "Dragon_Ball_Z_Heavy_Kick.mp3"
LEAP = "Dragon_Ball_jumping.mp3"
LEAP_BIG = "Dragon_Ball_Z_Jump.mp3"
KAMEHAMEHA = "Kamehameha_Charge_And_Blast.mp3"
NIMBUS = "Nimbus_Cloud.mp3"

CLIPS = {
    "punch": (PUNCH, 0.095, 0.50, 0.08, -15),
    "heavy_punch": (HEAVY_PUNCH, 0.10, 0.80, 0.25, -15),
    "heavy_kick": (HEAVY_KICK, 0.12, 0.85, 0.25, -15),
    "swing": (LEAP, 0.074, 0.34, 0.10, -20),
    "swing_big": (LEAP_BIG, 0.011, 0.40, 0.12, -19),
    "leap": (LEAP, 0.074, 0.62, 0.18, -17),
    "leap_big": (LEAP_BIG, 0.011, 0.62, 0.20, -17),
    "land_tap": (LEAP, 0.80, 1.015, 0.04, -18),
    "nimbus": (NIMBUS, 0.0, 2.2, 0.30, -19),
}
FIRE = {"kame_fire": (7.0, 9.6, 0.55), "kame_fire_short": (7.0, 8.15, 0.45)}
FIRE_RMS = -14

SHOUTS = {"shout_ha": ("VO_ADV_COM_J-00-001", -15), "shout_ha2": ("VO_ADV_COM_J-00-002", -15),
          "shout_ya": ("VO_ADV_COM_J-00-003", -15), "shout_arya": ("VO_ADV_COM_J-00-004", -15),
          "shout_orya": ("VO_ADV_COM_J-00-005", -15), "shout_aryaa": ("VO_ADV_COM_J-00-008", -15),
          "shout_haa": ("VO_ADV_COM_J-00-007", -15), "yatta": ("VO_ADV_COM_J-00-033", -16)}
VOICE_MARGIN = 0.005
ENGLISH = {"rock": "001", "scissors": "002", "paper": "004",
           "shout_ha": "002", "shout_ha2": "012", "shout_ya": "003", "shout_arya": "004",
           "shout_orya": "006", "shout_aryaa": "009", "shout_haa": "008", "yatta": "034", "throw": "004",
           "jump1": "001", "jump2": "002", "jump3": "012", "double_jump": "005", "triple_jump1": "016", "triple_jump2": "024",
           "long_jump": "014", "bonk": "032", "ledge": "011", "land": "000", "hurt": "019", "falling": "021", "lift": "018",
           "start": "028", "lets_go": "027", "game_over": "037", "burned": "015", "panting": "023", "tired": "023", "dying": "010",
           "ha": "008"}
ENGLISH_CHANT = {"ka": (0.0, 0.195), "me": (0.195, 0.345), "ha2": (0.345, 0.57), "me2": (0.57, 1.04)}

RISE = (0.86, 6.40)
RISE_RMS = -18
RISE_SECONDS = 3.1
RISE_STEPS = 6
STEP_EVERY = 0.5
STEP_OVERLAP = 0.1


def load(file, start, end, tempo=None, source=SOURCE):
    filters = [f"atrim=start={start}:end={end}", "asetpts=PTS-STARTPTS"]
    if tempo:
        filters.append(f"atempo={tempo}")
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(source / file), "-af", ",".join(filters),
                          "-ac", "1", "-ar", str(RATE), "-f", "f32le", "pipe:1"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32).copy()


def fade(pcm, fade_in, fade_out):
    for length, ramp, part in ((int(fade_in * RATE), 1, 0), (int(fade_out * RATE), -1, -1)):
        if length:
            line = np.linspace(0, 1, length)[::ramp]
            if part == 0:
                pcm[:length] *= line
            else:
                pcm[-length:] *= line
    return pcm


def rms_gain(pcm, target):
    return 10 ** (target / 20) / max(float(np.sqrt(np.mean(pcm ** 2))), 1e-6)


def write(name, pcm):
    peak = float(np.abs(pcm).max())
    if peak > 0.97:
        pcm = pcm * 0.97 / peak
    soundfile.write(SOUND / f"goku_{name}.ogg", pcm, RATE, format="OGG", subtype="VORBIS")
    print(f"goku_{name}.ogg {len(pcm) / RATE:.3f} s, peak {20 * np.log10(np.abs(pcm).max()):.1f} dB")


def shout(clip, rms):
    """A voice clip cut to its sound, with no silence ahead of it to delay the shout."""
    pcm = load(f"{clip}.brwav.wav", 0, 60, source=VOICE)
    loud = np.flatnonzero(np.abs(pcm) > np.abs(pcm).max() * 0.03)
    pcm = pcm[max(0, loud[0] - int(VOICE_MARGIN * RATE)):loud[-1] + int(0.03 * RATE)]
    return fade(pcm * rms_gain(pcm, rms), 0.002, 0.03)


def main():
    SOUND.mkdir(parents=True, exist_ok=True)
    for name, (file, start, end, out, rms) in CLIPS.items():
        pcm = load(file, start, end)
        write(name, fade(pcm * rms_gain(pcm, rms), 0.003, out))
    for name, (clip, rms) in SHOUTS.items():
        write(name, shout(clip, rms))
    for name, take in ENGLISH.items():
        write(f"en_{name}", shout(f"VO_ADV_COM_E-00-{take}", -15))
    chant = "VO_ADV_COM_E-00-007.brwav.wav"
    gain = rms_gain(load(chant, 0, 60, source=VOICE), -15)
    for name, (start, end) in ENGLISH_CHANT.items():
        write(f"en_{name}", fade(load(chant, start, end, source=VOICE) * gain, 0.004, 0.02))

    long = load(KAMEHAMEHA, *FIRE["kame_fire"][:2])
    gain = rms_gain(long, FIRE_RMS)
    for name, (start, end, out) in FIRE.items():
        write(name, fade(load(KAMEHAMEHA, start, end) * gain, 0.002, out))

    rise = load(KAMEHAMEHA, *RISE, tempo=(RISE[1] - RISE[0]) / RISE_SECONDS)
    rise *= rms_gain(rise, RISE_RMS)
    every, overlap = int(STEP_EVERY * RATE), int(STEP_OVERLAP * RATE)
    for step in range(RISE_STEPS):
        start = step * every
        write(f"kame_rise{step + 1}", fade(rise[start:start + every + overlap].copy(), STEP_OVERLAP, STEP_OVERLAP))


SONG_RATE = 32000


def song():
    files = sorted(p for p in (ROOT / "private/music").glob("*") if p.suffix.lower() in (".mp3", ".ogg", ".flac", ".wav", ".m4a", ".opus"))
    if not files:
        return
    out = SOUND / "goku_wing_song.ogg"
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(files[0]), "-vn", "-ac", "2", "-ar", str(SONG_RATE),
                          "-af", "loudnorm=I=-18:TP=-2", "-f", "f32le", "pipe:1"], capture_output=True, check=True).stdout
    pcm = np.frombuffer(pcm, dtype=np.float32).reshape(-1, 2)
    with soundfile.SoundFile(out, "w", SONG_RATE, 2, format="OGG", subtype="VORBIS") as file:
        for start in range(0, len(pcm), SONG_RATE):
            file.write(pcm[start:start + SONG_RATE])
    print(f"{out.name} {len(pcm) / SONG_RATE:.1f} s from {files[0].name}")


if __name__ == "__main__":
    song()
    main()
