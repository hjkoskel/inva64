# Invataxi 64

Invataxi for the Commodore 64, written in C with [cc65](https://cc65.github.io/).

You drive the invataxi. A passenger says where they want to go, and you have
about five seconds to click the right place on the map.

Repository: <https://github.com/hjkoskel/inva64>

## Playthrough video

[![Invataxi 64 playthrough on YouTube](https://img.youtube.com/vi/kUdvJCB3U7g/hqdefault.jpg)](https://youtu.be/kUdvJCB3U7g)

Click the picture to watch the playthrough on YouTube.

## How to play

1. Load the disk: `LOAD"*",8,1` and `RUN`, or autostart `inva64.d64` in an
   emulator. The title picture stays on screen while the game loads. On a
   real 1541 drive this takes almost three minutes.
2. When the music starts and the title shows **READY**, press any key or the
   fire button.
3. Listen to where the passenger wants to go, move the cursor to that place
   on the map, and press fire.

| Control | Joystick (port 2) | Keyboard |
|---|---|---|
| Move the cursor | stick | W, A, S, D |
| Click | fire | SPACE or RETURN |

Rules:

- **Right place:** you get 15 money.
- **Wrong place:** you lose a life. You start with three; the game ends when
  you make a mistake with none left.
- **Too slow:** you lose 15 money (never below 0).
- **KUOLIT:** the game over screen shows the money you gained. Press fire or
  any key to start again.

## What is in it

- A multicolor title picture and a hires map (320 x 200).
- 21 digitized speech clips at 6594 Hz, played through the SID volume
  register. They are vector quantised (5 samples per byte, a shared codebook
  of 256 entries), with a silence escape for pauses.
- The HARMONIA tune as SID music, converted from a ProTracker module with
  GoatTracker. It plays all the time except while a clip or a sound effect
  plays.
- Everything fits in memory at once: the game loads from disk only at the
  start.

## Building

Requirements: cc65, python3, ffmpeg, a host C compiler (gcc/cc) and VICE
(for `c1541` and `x64sc`).

```sh
make          # builds inva64.d64
make run      # starts it in VICE (x64sc)
make test     # plays the game in VICE and checks the rules
make clean
```

At every link the build prints how many bytes are free in each memory area.

Settings in the `Makefile`:

| Variable | Default | Meaning |
|---|---|---|
| `RATE` | 6594 | Sample rate of the clips in Hz |
| `VQ_LEN` | 5 | Samples per byte of clip data |
| `CLIP_GAIN` | 1.5 | Loudness boost of the clips (1 = off) |
| `MUSIC_VOLUME` | 10 | Master volume of the music, 0-15 |
| `CLIPS` | | Numbers of the clips that are built in |

Game tuning (reward, penalty, lives, answer time, delays, cursor speed,
sound effects) is in `src/config.h`.

## Files

| Path | Contents |
|---|---|
| `src/` | Game sources: C for the game logic, assembly for the boot loader, the frame interrupt and the sample player; linker configs |
| `tools/` | Build tools: sample encoder, picture and music converters, memory report |
| `tests/` | Automated play test through the VICE remote monitor |
| `invatitle.kla` | Title picture (Koala format) |
| `kartta/` | The map picture and the scripts that made it |
| `invasoundboard/` | The speech clips (`wav/`) and the sound board program the sample player comes from |
| `harmonia_small.sid` | The music |
| `initialIdea.md` | The game specification |
| `INVA64PLAN.md` | Implementation plan, memory layout and status |

The disk image has two files. `INVATAXI` is a small boot file: it shows the
title picture and loads `MAIN`, which is the game. `INVA64PLAN.md` describes
the memory layout in detail.

## Credits

Original idea and graphics: **Åkesoft**

Credits of the original DOS game:

| Role | Credit |
|---|---|
| Composition | Jorma Kaapeli, Kekkonen |
| Music | Tfosekä |
| Coding | Kekkonen |
| Yodeling | Zorro |
| GFX | Tom Of Svenland |
| Source | Karma Joopeli |

## Target

PAL Commodore 64 with a 1541 disk drive. On NTSC the game runs, but the
music plays about 20% too fast.
