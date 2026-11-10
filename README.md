# Kid Goku for sm64coopdx

Kid Goku from the original Dragon Ball, in his Pilaf-saga gi, as a Character Select add-on for sm64coopdx.

## Install

You need:

- sm64coopdx 1.5.1
- [Character Select](https://github.com/Squishy6094/character-select-coop) 1.16.3

Then:

1. Download `kid-goku-v1.0.0.zip` from this repository's Releases.
2. Unzip it into sm64coopdx's mods folder, so that the folder holds `kid-goku/main.lua`:
   - Windows: `%appdata%\sm64coopdx\mods`
   - macOS: `~/Library/Application Support/sm64coopdx/mods`
   - Linux: `~/.local/share/sm64coopdx/mods`
3. Host a game with both **Character Select** and **[CS] Kid Goku** turned on.
4. Open Character Select and pick Kid Goku.

Everyone in the room needs the same mods turned on.

## Moves

A, B and Z are the N64 controller's own buttons, as in Super Mario 64. Y is the extra button sm64coopdx adds: by
default it is Y on a modern gamepad and M on a keyboard. An N64 controller has no Y, so bind it to a spare button in
sm64coopdx's Options, under Controls.

| Input | Move |
|---|---|
| B | Jan Ken combo: Rock, Scissors, Paper |
| Hold B, release | Kamehameha, on the ground or in the air |
| B while walking | High side kick |
| B at a run | Boot-first lunge |
| B in the air | Flying kick |
| Y | Flying Nimbus: the stick steers, A climbs, Z sinks, Y gets off |
| Wing cap | The four-star Dragon Ball: the third jump calls the Nimbus |

His voice is Japanese. Turn on **English Voice** in the mod's menu to hear the English one; the setting only changes
what you hear.

## Build

The zip in Releases is already built. To build it yourself you need:

- Node.js 20 or later
- Python 3 with `scripts/requirements.txt` installed, in a virtual environment
- Blender 5.3 with the Fast64 add-on
- FFmpeg
- A checkout of sm64coopdx 1.5.1's source, for its Lua constants

Folders under `private/` are ignored by Git. They hold what the build reads and never ships in the repository.

1. Write `private/check.env`:

   ```sh
   PYTHON=/path/to/venv/bin/python
   SM64_ROM=/path/to/your/sm64.us.z64
   COOPDX_BIN=/path/to/sm64coopdx
   CHARACTER_SELECT=/path/to/character-select-coop
   ```

   Only `PYTHON` is needed to build; the rest are for the in-game checks.

2. Unpack Character Select's pack template so that this file exists:
   `private/downloads/template/char-select-template-main/actors/template.blend`

3. Optional: put your own model source at `private/rips/kid-goku/chara011_1p.gltf`. Without it the build makes a
   simpler model in code.

4. Build the textures, the model, the props and the animations:

   ```sh
   "$PYTHON" scripts/textures.py
   ```

   ```sh
   SM64COOPDX_CONSTANTS=/path/to/sm64coopdx/autogen/lua_definitions/constants.lua node scripts/build.mjs
   ```

   Set `BLENDER` if Blender is not at `/Applications/Blender 5.3.app/Contents/MacOS/Blender`.
   The build writes `mod/kid-goku/actors/` and `mod/kid-goku/anims-data.lua`.

5. Build the sounds into `mod/kid-goku/sound/`. The mod runs without them and uses the game's own sounds.

   ```sh
   "$PYTHON" scripts/sounds.py --disc "/path/to/SLUS-21678.iso"
   ```

   ```sh
   "$PYTHON" scripts/sfx.py
   ```

   `sounds.py` reads the Japanese battle voice from your own disc image. `sfx.py` trims the effect and voice files
   it names from `private/sfx/` and `private/voice/`.

6. Zip the mod folder:

   ```sh
   cd mod && zip -r ../kid-goku.zip kid-goku -x "*.DS_Store"
   ```

`scripts/check.mjs` and `scripts/check-pair.mjs` play the mod headless in a real game. They use a separate game
runner that is not part of this repository.

## License

Kid Goku mod © 2026 Metal Fox. Free to use, change and share under [Creative Commons Attribution 4.0](LICENSE): if you use it, credit Metal Fox.

## Credits

- Kid Goku mod: Metal Fox
- Character Select: Squishy6094
- Kid Goku's voice: *Dragon Ball Z: Budokai Tenkaichi 3*
- Dragon Ball belongs to Akira Toriyama, Shueisha and Toei Animation. Super Mario 64 belongs to Nintendo. This is a
  fan project with no ties to either.
