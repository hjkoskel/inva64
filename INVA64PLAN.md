# INVA64 implementation plan

Plan for implementing the Invataxi game on the Commodore 64 in C (cc65), based
on `initialIdea.md` and the material in this directory.

## 1. Decisions and assumptions

Decided with the author:

| Topic | Decision |
|---|---|
| Delivery | A `.d64` disk image with two files: a small **boot** file (title picture + loader) and the **main** game file. |
| KIRPPUTORI | It is on the map but is never asked for. A click on it counts as a wrong place. |
| Sample 4 "uuaaa" | Left out of the build. Samples 9 and 15 are left out too ("skip this"). |
| Sound quality | Stays the same as in the soundboard: 6594 Hz, `VQ_LEN=5`. The build uses a fixed rate and does not lower it to make things fit. |

Assumptions made in this plan (change them here if they are wrong):

- **PAL** is the target. On NTSC the game runs, but the music is about 20% fast.
- Joystick in **port 2**. Keyboard: W/A/S/D move, SPACE or RETURN is fire.
- A click on empty ground (no click area) is ignored.
- The cursor does not move while a sample plays, because sample playback
  blocks interrupts and uses the whole CPU (as in the soundboard).
- Lives: the game starts with 3, and it ends when lives go below 0, so the
  4th wrong click ends it (as written in the idea).
- The same place is not asked twice in a row. This is an addition to the idea.
- After KUOLIT the game goes straight back to the playfield, not to the title.
- Boot loader, sample player, IRQ handler and music player are assembly
  (ca65). All game logic is C.

## 2. Material in this directory

| Path | What it is | Use in the game |
|---|---|---|
| `invatitle.kla` | Koala multicolor picture (10003 bytes: load address, 8000 bitmap, 1000 screen, 1000 colour, 1 background) | Loader and title screen |
| `kartta/kartta_hires.art` | Hires map (Art Studio: 8000 bitmap + 1000 screen) | Playfield. Used directly, so `hires.py` and PIL are not needed in the build |
| `kartta/kartta_nayta.c` | Shows the map with cc65 `inflatemem`, VIC bank 3, bitmap at `$E000` | Basis for the playfield display code |
| `invasoundboard/` | VQ sample encoder (`mksamples.py`, `vqenc.c`) and player (`play.s`) | Basis for the sample tool and the sample player |
| `invasoundboard/wav/` | 24 clips, 8-bit 12 kHz | Sample sources (21 of them are used) |
| `harmonia_small.sid` | The HARMONIA music as a PSID v2 file (1602 bytes), packed with GoatTracker. See section 2.1 | **The music source for the game** |
| `harmonia_small_run.prg` | A stand-alone test program that plays the same music from a raster interrupt | Reference for how the player is called |

Installed tools: cc65 2.18, VICE (`x64sc`, `c1541`), python3, ffmpeg, gcc, go.
Not installed: GoatTracker (`gt2reloc`), Exomizer, PIL. The plan does not need them.

### 2.1 What is inside `harmonia_small.sid`

Read from the file header and a disassembly of the data:

| Field | Value |
|---|---|
| Format | PSID version 2, 124-byte header, 1 song, title "Harmoniaa kansalle" |
| Data | 1476 bytes, loads to `$0FF6-$15B9` |
| Init address | `$0FF6` |
| Play address | `$1003` |
| Speed flag | CIA timer (not the 50 Hz frame interrupt) |
| Flags | PAL, 6581 |
| Zero page | `$FC-$FD` |

The data has two parts:

- **`$0FF6-$0FFF` (10 bytes):** a small wrapper. It sets CIA1 timer A to
  `$998E` and jumps to the real init routine.
- **`$1000-$15B9` (1466 bytes):** the GoatTracker player and the song, with
  the usual entry points: init at `$1000` (A = song number 0), play at `$1003`.

The game uses only the second part. It does not use the wrapper, because the
game drives the player from its own frame interrupt and CIA1 timer A is not
free to be reprogrammed by the music.

**Playback speed: 50 calls per second** (decided by the author). The game
does what `harmonia_small_run.prg` does: it calls the play routine once per
frame from a raster interrupt. The timer value in the `.sid` wrapper (39311
cycles, about 25 calls per second) is ignored.

## 3. Game flow

```
BOOT      title picture on, main file loads from disk
READY     music starts, the title shows a blinking "READY" text
          any key or the fire button -> INTRO
INTRO     wait 0.5 s -> sample 1 -> wait 1 s -> sample 3 -> wait 1 s
PLAYFIELD map on, money 0, lives 3
ROUND     wait 1 s, then pick place (random, not the previous one)
          play prefix (random: 2, 5 or 6), then the place sample
          start timer (5 s), player moves the cursor
            fire on the right place  -> money += 15, sample 8,  next ROUND
            fire on a wrong place    -> sample 11, lives -= 1, "blonk" effect
                                        lives < 0 -> KUOLIT, else next ROUND
            timer runs out           -> sample 7, money -= 15 (not below 0),
                                        three beeps if money was lost, next ROUND
KUOLIT    text screen: "KUOLIT" and the money gained
          fire or any key -> money 0, lives 3 -> PLAYFIELD
```

The music plays all the time except while a sample plays.

Place and sample numbers:

| Place | Sample | | Place | Sample |
|---|---|---|---|---|
| UIMAHALLI | 10 | | ANKKALINNA | 19 |
| DRUGS | 12 | | KIRJASTO | 20 |
| MAKKARI | 13 | | SAIRAALA | 21 |
| KUKKIA | 14 | | POLIS | 22 |
| RKIOSKI | 16 | | RAUTAA | 23 |
| SORSAPUISTO | 17 | | SIWA | 24 |
| WC | 18 | | KIRPPUTORI | none, always wrong |

Click areas come from the table in `initialIdea.md` (14 areas). The first
matching area wins.

All tunable numbers go into `src/config.h`: `MONEY_REWARD 15`,
`TIMEOUT_PENALTY 15`, `START_LIVES 3`, `ANSWER_FRAMES 250`, the intro delays
and the cursor speed.

## 4. Memory

### 4.1 Layout

```
$0334-$03FB  loader stub (copied here by boot, used only while loading)
$0400-$07FF  ONE-SHOT zone: compressed map screen data + intro-only code.
             After the intro this is the text screen for KUOLIT.
$0800-$0FFF  cc65 startup, VQ codebook (1280 bytes), small tables
$1000-$15B9  music player + song (1466 bytes cut from harmonia_small.sid)
$15BA-$BFFF  C code, sample clips, compressed map bitmap
$C000-$CBFF  sprite data, BSS, C stack (256 bytes); spare space holds clips
$CC00-$CFE7  bitmap screen RAM (title first, then the map)
$D000-$DFFF  RAM under I/O: sample clips, copied in by the boot file
$D800-$DBE7  colour RAM (title only; hires does not use it)
$E000-$FF3F  bitmap (title first, then the map), RAM under the KERNAL
$FFFA-$FFFF  RAM vectors (NMI -> RTI) for when the KERNAL is banked out
```

VIC bank 3 is used for both pictures. The KUOLIT text screen uses bank 0,
because the character ROM is not visible in bank 3.

The main file loads to `$0400-$CBFF` in one piece. While it loads, the VIC
shows the title from bank 3, so the data going through `$0400` is not visible.

### 4.2 How the one-time data is reused

- **Title picture:** costs no game memory. It is in the boot file and is
  copied to the bitmap area. The map is later unpacked over it.
- **Compressed map screen data and intro code:** in `$0400-$07FF`, which
  becomes the KUOLIT text screen.
- **Samples 1 and 3 and the compressed map bitmap** (7.8 KB together): there
  is no generated data left to put in their place, so with a single load they
  stay in memory. Reusing them needs a second disk load after the intro, which
  would stop the music for many seconds. This is lever 5 in section 4.4.

### 4.3 Budget

Sizes are measured from the existing builds at 6594 Hz.

| Item | Bytes |
|---|---:|
| **Available:** `$0400-$CBFF` | 51200 |
| **Available:** `$D000-$DFFF` | 4096 |
| **Total available** | **55296** |
| Game clips (19 clips: 2, 5-8, 10-14, 16-24) | 37973 |
| Startup clips 1 and 3 | 4888 |
| VQ codebook | 1280 |
| Music | 1466 |
| Compressed map (bitmap 2436 + screen 470) | 2906 |
| BSS (765 of it is `inflatemem` work area), stack, sprites | ~1350 |
| **Total fixed** | **~49860** |
| **Left for all code and tables** | **~5400** |

`inflatemem` takes 503 bytes of that code. The soundboard's C program is about
1.1 KB, so 5.4 KB is tight but realistic if the C code is written carefully:
no `printf`, no conio, `unsigned char` variables, static variables instead of
locals, and a small hand-written text routine for KUOLIT.

The linker fails the build if a memory area overflows. The build also prints
the free bytes of each area after every link.

### 4.4 Levers if it does not fit

In order of preference. None of them changes the sound quality.

1. **Silence escape in clips** (idea 3 in `SOUNDBOARD.md`): one codeword means
   "silence for n vectors". Saves about 7% of clip data (~3 KB) for a few
   lines in the player.
2. **Smaller unpacker:** replace `inflatemem` (503 bytes code + 765 bytes BSS)
   with a simple LZ or RLE unpacker written for this map. The packed map grows
   a little, but the total shrinks.
3. **Move hot C functions to assembly** (hit test, number drawing, input).
4. **Trim leading and trailing silence harder** in `mksamples.py`.
5. **Second disk load:** put samples 1 and 3 and the map unpacker in an intro
   file, and load the last part of the game clips over them after the intro.
   Saves about 8 KB, at the cost of a silent disk load before the playfield.

## 5. Technical design

### 5.1 Boot file (`boot.s`, assembly, about 14.3 KB)

Loads to `$0801` with a BASIC `SYS` line. Contents: code, the title picture
and 4096 bytes of clip data for `$D000`.

1. `SEI`, set `$01=$34` (all RAM), copy the title bitmap to `$E000` and the
   clip data to `$D000`, then restore `$01`.
2. Copy the title screen data to `$CC00` and the colour data to `$D800`. Set
   the background colour from the Koala file and the border to black.
3. Set the VIC: bank 3, `$D018=$38`, multicolor bitmap mode.
4. Copy the loader stub to `$0334` and jump to it.
5. The stub turns KERNAL messages off, loads `MAIN` from the device in `$BA`
   to `$0400`, and jumps to the main entry address. On a load error it turns
   the border red and stops.

The main entry address is taken from the main program's label file at build
time, so the main program is built first.

A stock 1541 needs about 2 minutes for the 50 KB main file. A fast loader is
not part of this plan.

### 5.2 Main program start-up

- Custom linker config `src/inva64.cfg` (based on `soundboard.cfg`): no BASIC
  header, memory areas as in 4.1, the music at a fixed `$1000`.
- Start-up code sets up the C stack and BSS, then calls `main()`. It must not
  touch the VIC, so the title stays on screen.

### 5.3 Frame interrupt and music (`irq.s`)

- A raster interrupt once per frame through the KERNAL vector `$0314`; the CIA1
  timer interrupt is turned off. The handler ends with `JMP $EA81`, which
  skips the KERNAL keyboard scan.
- The handler adds 1 to a frame counter and calls the music play routine
  `$1003` unless `music_paused` is set: once per frame, 50 times per
  second on PAL, as in `harmonia_small_run.prg`.
- At start-up the main program calls the music init routine at `$1000` with
  A = 0. It does not call the `.sid` init address `$0FF6`.
- The cc65 zero page area is `$02-$1B`, so the player's `$FC-$FD` does not
  clash with it. The KERNAL does not use `$FB-$FE`.
- All timing in C (delays, the 5 s answer time) uses the frame counter.

### 5.4 Sample player (`play.s`, from the soundboard)

Changes to the soundboard version:

- Each index byte is read with `$01=$34` and the SID is written with
  `$01=$35`, so clips can be anywhere, including `$D000-$DFFF`. This costs
  about 10 cycles per 5 samples.
- Before playing: set `music_paused`, then set the three voices to the
  constant level the soundboard uses for the 8580.
- After playing: clear the voice control registers, set the volume to 15 and
  clear `music_paused`. The song goes on from the same position. Notes that
  were sounding come back at their next note-on.

`play_clip(id)` is the only C interface. It returns when the clip has ended.

### 5.5 Sample tool (`tools/mksamples.py`, from the soundboard)

- Takes a list of clip numbers (all except 4, 9 and 15) and trains the
  codebook on those only.
- New option `--rate 6594`: fixed rate, no search.
- The "hi" area becomes `$D000-$DFFF` (4096 bytes). The existing subset-sum
  code picks the clips that fill it best. The tool writes that data as a
  binary for the boot file. The same idea fills the spare space in
  `$C000-$CBFF`.
- Writes `samples.h` with clip ids named after their purpose
  (`CLIP_KIITTI`, `CLIP_PLACE_WC`, ...).

### 5.6 Pictures (`tools/mkgfx.py`, python standard library only)

- Splits `invatitle.kla` into bitmap, screen, colour and background for the
  boot file.
- Reads `kartta/kartta_hires.art`, compresses the bitmap and the screen data
  with raw deflate (as `hires.py` does) and writes them as binaries.

### 5.6b Music (`tools/mkmusic.py`, python standard library only)

- Reads `harmonia_small.sid`, checks the header (`PSID`, play address `$1003`,
  data covering `$1000`) and writes the bytes from `$1000` to the end as
  `build/music.bin`. The 10-byte wrapper before `$1000` is dropped.
- The build stops with a clear message if the header does not match, for
  example when a new version of the tune is packed for another address.
- `music.s` includes the binary into the `MUSIC` segment, which the linker
  config places at `$1000`.

To change the music, replace `harmonia_small.sid` and rebuild. The new file
must be packed for `$1000` with zero page `$FC`.

### 5.7 Playfield (`playfield.c`)

- `playfield_show()`: screen off, unpack the bitmap to `$E000` (with `SEI` and
  the ROMs banked out, as in `kartta_nayta.c`), unpack the screen data to
  `$CC00`, hires mode, screen on, cursor sprite on. This runs once. The bitmap
  stays in memory during KUOLIT, so it is not unpacked again. The music stops
  for the 1-2 seconds this takes; that is the "pause" in the idea.
- **Money:** up to 5 digits after the "MONEY" label on the bottom row. Each
  digit is 8 bytes copied from the character ROM into the bitmap, so no font
  data is needed. Redrawn only when the money changes.
- **Lives:** one marker for each life left, next to the "EMÄLÄT" sign. The
  exact cells are chosen in phase 4 by looking at the picture.
- `playfield_hit(x, y)`: returns the place index or -1, from the click-area
  table.

### 5.8 Cursor and input (`input.c`)

- Sprite 0, a hires arrow. The hot spot is the top-left pixel. The position is
  kept in map pixels (x 0-319, y 0-199) and converted to sprite coordinates
  (x+24, y+50, with the 9th x bit).
- Joystick port 2 is read from `$DC00`. W/A/S/D, SPACE and RETURN are read by
  scanning the keyboard matrix directly, so several keys work at once.
- Movement once per frame: 1 pixel per frame at first, faster while the
  direction is held.
- Fire is edge-triggered: one click per press.

### 5.9 Game logic (`main.c`, `game.c`)

- A simple loop following the flow in section 3. The states are functions.
- Random numbers: a small 16-bit generator, seeded from the CIA timer and the
  raster position, and stirred again with the frame counter at every click.
- KUOLIT (`kuolit.c`): switch to bank 0 text mode, clear `$0400-$07E7`, write
  "KUOLIT" and the money with direct screen writes, wait for fire or a key,
  then switch back to the map.

## 6. Source tree

```
inva64/
  Makefile
  INVA64PLAN.md
  src/
    config.h      tunable constants
    main.c        start-up, intro, main loop
    game.c        round logic, money, lives
    playfield.c   map display, money and lives display, hit test
    input.c       joystick, keyboard, cursor sprite
    kuolit.c      game over screen
    boot.s        boot file: title + loader
    irq.s         frame interrupt, music calls
    play.s        VQ sample player
    music.s       includes build/music.bin at $1000
    inva64.cfg    linker config for the main file
    boot.cfg      linker config for the boot file
  tools/
    mksamples.py  sample encoder (from invasoundboard)
    vqenc.c       VQ trainer (from invasoundboard, unchanged)
    mkgfx.py      title and map conversion
    mkmusic.py    cuts the player and song out of harmonia_small.sid
  build/          generated files
  inva64.d64      result: "INVATAXI" (boot, autostarts) + "MAIN"
```

The existing directories (`invasoundboard`, `kartta`) stay as they are. The
build reads the wav files and the `.art` file from them, and `invatitle.kla`
and `harmonia_small.sid` from the project root.

Make targets: `make` (builds the d64), `make run` (starts it in `x64sc`),
`make clean`.

## 7. Implementation phases

Each phase ends with something that runs in VICE.

| # | Phase | Done when |
|---|---|---|
| 1 | **Build skeleton.** Makefile, linker configs, `mkgfx.py`, boot file, an empty main program that only changes the border colour. | `make run` shows the title picture, loads `MAIN`, and the border changes. |
| 2 | **Music.** `mkmusic.py`, frame interrupt and the music at `$1000`. | The music plays over the title picture and loops, at the same speed as `harmonia_small_run.prg`. |
| 3 | **Samples.** Adapted `mksamples.py` and `play.s`, clips under I/O, pause and resume of the music. Intro sequence. | Samples 1 and 3 play over the title with the right delays, and the music continues after them. Every clip plays correctly in a test loop, including the clips at `$D000`. |
| 4 | **Playfield.** Map unpacking, cursor sprite, joystick and keyboard, money and lives display. | The map appears after the intro. The cursor moves over the whole map with both inputs. A test mode shows the index of the clicked area. |
| 5 | **Game logic.** Rounds, timer, rewards and penalties, KUOLIT, restart. | The whole flow in section 3 works. |
| 6 | **Memory and polish.** Check the free bytes, apply levers from 4.4 if needed, tune delays and cursor speed, check on both SID models in VICE (6581 and 8580). | The d64 autostarts and plays from start to KUOLIT and back with no glitches. |

Memory is checked from phase 3 on: the sample data is the largest item, so it
goes in early and the code grows into what is left.

## 8. Risks

| Risk | What to do |
|---|---|
| Code does not fit in ~5.4 KB | Levers in 4.4, starting with the silence escape. |
| Music sounds wrong after a sample (voices left in a bad state) | Re-initialise the SID registers the player does not rewrite every frame; test by ear in phase 3. |
| Clicks or noise when switching between music and samples | Ramp the volume register to the mid level before and after a clip. |
| Joystick in port 2 causes false key presses in the matrix scan | Read the joystick first and skip the key scan while a joystick direction is active. |
| A later version of `harmonia_small.sid` is larger or packed for another address | `mkmusic.py` stops the build if the address is wrong. A larger song takes memory from the code (section 4.3). |
| Long load time on a real 1541 | Accepted for now. A fast loader can be added later without changing the game. |

## 9. Open items

- Where sample 4 "uuaaa" is used, if anywhere (it is out of the build for now).
- The exact look of the lives display next to "EMÄLÄT".
- Whether a high-score list or the DOS version's start menu is wanted later.
  Neither is in this plan.

## 10. Implementation status

Phases 1-5 are implemented. `make` builds `inva64.d64`, and `make test` plays
the game in VICE and checks the rules (see below).

Memory after the build (from `tools/memreport.py`, printed at every link):

| Area | Used | Free |
|---|---:|---:|
| `$0400` one-shot zone | 778 | 246 |
| `$0800` low area | 1539 | 509 |
| `$1000` music | 1466 | 0 |
| `$15BA` code, clips, BSS | 42908 | 3498 |
| `$D000` clips under I/O | 4086 | 10 |

The C code is about 3.6 KB. Lever 1 of section 4.4, the silence escape, is
implemented: the clip data went from 42861 to 39108 bytes (39902 with the
loudness boost). The other levers
were not needed.

How the silence escape works: one codeword (`VQ_ESC`, all samples at the mid
level 8) is followed by a count byte n and is played n times. The encoder
stores runs of vectors that hold only the levels 7 and 8 this way, so a pause
loses at most its 1-step noise and everything else is unchanged.

Differences from the plan above:

- **Main entry address** is fixed at `$0800`, so the boot file does not need
  the main program's label file.
- **Music during the map unpack:** the music keeps playing. The frame
  interrupt also works with the KERNAL banked out (a RAM vector at `$FFFE`).
- **Music volume:** the player's master volume is patched from 15 to 10 at
  build time (`MUSIC_VOLUME` in the Makefile), because the samples are much
  quieter than the music on the 8580. Set it to 15 for the original level.
- **READY screen** (added to the specification later): when the main file
  has loaded, the music starts and the title shows "READY" until a key or the
  fire button is pressed. The text is two double-size sprites built from the
  character ROM, with two black copies behind them as a shadow. Position and
  blink rate are in `config.h`. The random seed is taken at the key press.
- **Sound effects** (added to the specification later): a "blonk" (a pulse
  tone sliding down, about 0.3 s) when a life is lost, and three short beeps
  when money is lost. There are no beeps when the money was already 0. The
  effects use SID voice 1 while the music waits; pitch, length and volume are
  in `config.h`.
- **Round delay:** 1 s before the next place is picked (`ROUND_GAP_FRAMES`).
- **Clip volume:** two changes make the clips louder. (1) The sample
  player now turns the gate of the three SID voices off and on again before
  a clip. The music often leaves the gates on, and then the envelopes did not
  rise to full level, which made the clips much quieter than in the
  soundboard. (2) The encoder has a loudness boost (`CLIP_GAIN` in the
  Makefile, now 1.5; 1 = off) that amplifies the clips and rounds off their
  peaks. The boost costs about 800 bytes, because pauses are less often pure
  silence.
- **Lives** are hearts on the bottom row, below the "EMÄLÄT" sign.
- **Cursor sprites** (white fill and black outline) are at `$FF40` and
  `$FF80`, in the free RAM above the bitmap.
- **Clips under I/O:** the tool picks the clips that fill the area best (now 8, 17 and 23).
- **`game.h`, `crt0.s`, `data.s`** and `tools/memreport.py` were added;
  `music.s` was merged into `data.s`.

What was checked, and how:

| Check | Result |
|---|---|
| Title shows, main file loads, READY appears and the game waits for a key, map appears (screenshots, `make test`) | pass |
| Rules: reward, timeout, clamp at 0, wrong place, KIRPPUTORI, empty ground, KUOLIT, restart (`make test`) | pass |
| Intro audio order: music, sample 1, music, sample 3, music (recorded at normal speed) | pass |
| A clip stored under I/O and a long clip with pauses play correctly with the silence escape (recordings compared with the encoder previews) | pass |
| Blonk after a wrong place and beeps after a timeout are in the recorded audio (falling pitch; three bursts near 900 Hz) | pass |
| Joystick and keyboard reading on a real key press | **not checked**: the test presses fire by patching `input_read()` |
| 6581 SID model, NTSC, real 1541 | not checked |

The main file takes about 2 min 45 s to load with true drive emulation.

Still open from phase 6: tuning of delays and cursor speed by hand, and a
check by ear of the music after each sample.
