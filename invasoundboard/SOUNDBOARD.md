# C64 Sound Board

A Commodore 64 program that plays 24 digitized sound clips. Type a clip
number (1–24), press RETURN, and the clip plays through the SID chip.

Written in C (cc65) with one small assembly routine for playback.

## The problem

The source clips are `wav/01_…wav` … `wav/24_…wav`: 8-bit mono, 12000 Hz,
**36.7 seconds** in total. Stored as they are, that is about **440 KB**. The
C64 has 64 KB of RAM, and only about 49 KB of it is free for data once the
program, screen, stack and I/O area are taken out.

So the sound has to shrink by about **9×**. The program also has to play
from RAM straight away, with no waiting for the disk.

## Current solution

### 1. Where the bits go

| Step | Size per second of audio |
|---|---|
| Original: 12000 Hz × 8 bit | 12000 bytes |
| Silence trimmed from the start and end of each clip | (~1–2% saved) |
| Resampled to ~6600 Hz | 6600 bytes |
| 4-bit output (the SID volume register is 4 bits wide) | 3300 bytes |
| **Vector quantization: 5 samples → 1 byte** | **~1320 bytes** |

### 2. Playing samples on the SID

The C64 has no DAC (digital-to-analog converter). The usual trick is to
write each sample to the 4-bit master volume register `$D418`. Every write
moves the SID output level, which turns the volume register into a crude
4-bit DAC.

The newer SID chip (8580) has almost no DC offset at its output, so this
trick is nearly silent on it. To fix that, `play_init` sets all three voices
to output a constant level (test bit + pulse waveform, gate on, sustain 15).
The volume register then scales that level, and the sound is audible on
both the 6581 and the 8580.

### 3. Vector quantization (VQ)

This is what makes 24 clips fit.

**Encoding** (on the PC, `tools/mksamples.py` + `tools/vqenc.c`):

1. Each clip is trimmed of silence and resampled. It then goes through a
   high-pass filter (120 Hz), a treble boost (+5 dB above 1.5 kHz) and a
   compressor, so quiet syllables survive the coarse quantization. Finally
   it is normalised to the 0..15 volume range.
2. All clips are cut into **vectors of 5 consecutive samples**.
3. k-means clustering finds the **256 vectors** that best represent all of
   them. This is the **codebook**, shared by all 24 clips. The codebook is
   then rounded to whole 4-bit values and the clips are encoded again
   against the rounded version, so the encoder sees exactly what the C64
   will play.
4. Each vector is stored as **one byte**: the number of its closest
   codebook entry. That is 1.6 bits per sample.

**Decoding** (on the C64, `src/play.s`) is just table lookups. The codebook
is stored as 5 tables of 256 bytes (1280 bytes), and table *j* holds sample
*j* of every entry:

```
loop:  lda (ptr),y          ; codeword number
       tax
       ldy codebook+0*256,x ; sample 0
       (wait for timer) sty $D418
       ldy codebook+1*256,x ; sample 1
       (wait for timer) sty $D418
       ...                  ; samples 2..4
```

The loop is generated with `.repeat VQ_LEN`, so the vector length is a
build setting.

### 4. Timing

The sample rate comes from CIA2 timer A, which is **polled**, not
interrupt-driven. The timer runs continuously and the player waits for each
underflow before writing the next sample. Code timing and VIC bad lines
(cycles stolen by the video chip) only cause a few cycles of jitter and
never change the speed.

The timer latch is `CPU clock / rate − 1`. Values for PAL (985248 Hz) and
NTSC (1022727 Hz) are generated at build time, and the program picks one
with `get_tv()`.

While a clip plays, interrupts are off and `$01 = $35`. BASIC and KERNAL ROM
are switched out, so the RAM under them can be read. The NMI vector at
`$FFFA` points to an `RTI`, so pressing RESTORE during playback is harmless.

### 5. Memory layout

```
$0801 ┌──────────────────────────────┐
      │ BASIC stub + C code (~1.1 KB)│
      │ VQ codebook (1280 bytes)     │
      │ clip data (indices)          │  single file: all 24 clips
      │   ...                        │  HQ version: 20 clips
$CCE9 │ (end of program)             │  ($CEAB in the HQ version)
$CF00 │ C stack (256 bytes)          │
$D000 │ I/O (VIC, SID, CIAs)         │
$E000 │ RAM under the KERNAL ROM     │  HQ version only: 4 clips
$FFF9 │ (loaded from "hisamples")    │  (8186 bytes)
$FFFA │ CPU vectors                  │
      └──────────────────────────────┘
```

Other memory savings:
- The C stack is cut from cc65's default 2 KB to 256 bytes (in
  `src/soundboard.cfg`).
- Only conio is used for text, not stdio.
- `.incbin` puts the sample data straight into the binary.

### 6. Picking the sample rate automatically

The build does not use a fixed sample rate. `mksamples.py` searches for the
**highest rate at which the codebook and all clips still fit** in
`LOW_BUDGET` bytes, plus the 8186-byte area under the KERNAL in the HQ
version.

In the HQ version, the script also chooses which clips go under the KERNAL.
It solves this exactly (a subset-sum problem), filling that 8 KB area as
fully as possible.

## Build outputs

| File | Contents | Sample rate | Noise level (SNR) |
|---|---|---|---|
| `soundboard.prg` | **Main version.** One file, all 24 clips. | 6594 Hz | 14.1 dB |
| `soundboard-hq.prg` | Also uses the RAM under the KERNAL. Needs the file `hisamples`. | 7725 Hz | 14.0 dB |
| `soundboard.d64` | Disk with `soundboard` (first, autostarts), `soundboard hq` and `hisamples`. | | |

`build/single/preview/*.wav` and `build/hq/preview/*.wav` hold exactly the
sample values the C64 plays. Use them to judge the quality on a PC.

If the HQ version starts without `hisamples` (for example, as a bare PRG),
it says so and keeps running. Only the 4 clips stored in that file are
unavailable.

## Building and running

Requirements: cc65, python3, ffmpeg, a host C compiler (gcc/cc) and VICE
(for `c1541` and `x64sc`).

```sh
make            # soundboard.prg, soundboard-hq.prg, soundboard.d64
make run        # run soundboard.prg in VICE
make run-d64    # autostart the disk image
make clean
```

On the C64, type a number from 1 to 24 and press RETURN. DEL removes a digit.
To use the HQ version from the disk:

```
LOAD"SOUNDBOARD HQ",8
RUN
```

A real 1541 drive loads ~50 KB slowly (1–2 minutes). In VICE, warp mode
(Alt+W) speeds this up.

### Settings

| Variable | Default | Meaning |
|---|---|---|
| `VQ_LEN` | 5 | Samples per byte. Higher = less memory per second, grainier sound. |
| `LOW_BUDGET` | 49000 | Bytes for codebook + clips inside the program. A higher value gives a higher rate; the build fails with an overflow error if it is too high. |

Example: `make clean && make VQ_LEN=6`

### Source files

| File | Purpose |
|---|---|
| `src/main.c` | UI, number input, loading `hisamples` |
| `src/play.s` | SID setup and the VQ playback loop |
| `src/soundboard.cfg` | Linker config: `SAMPLES` segment, 256-byte stack |
| `tools/mksamples.py` | Preprocessing, choosing the rate, memory layout, generated sources |
| `tools/vqenc.c` | k-means codebook training and encoding |

## Measured trade-offs

Measured on these 24 clips. Sizes include the codebook. The noise level is
the encoder's signal-to-noise ratio (SNR); higher is cleaner.

| Setting | Bytes (all clips) | vs. VQ_LEN 4 | SNR |
|---|---|---|---|
| VQ_LEN 4 @ 6208 Hz | 57168 | — | 15.4 dB |
| **VQ_LEN 5 @ 6208 Hz** | 46199 | −19% | 14.0 dB |
| VQ_LEN 6 @ 6208 Hz | 38969 | −32% | 13.1 dB |
| VQ_LEN 8 @ 6208 Hz | 30127 | −47% | 11.8 dB |
| VQ_LEN 4 @ 5500 Hz | 50765 | −11% | 15.4 dB* |

\* A lower sample rate does not add noise. It removes high frequencies
(duller sound), which this SNR figure does not capture.

For comparison, plain 4-bit samples (two per byte), the first version of
this program, needed 3300 bytes per second at 6600 Hz. The current version
needs 1320.

## Ideas for reducing memory further

Roughly in order of benefit for the effort.

1. **Longer vectors (`VQ_LEN=6` or `8`).** No code changes needed. −15% or
   −35% compared with the current setting, with gradually rougher sound.
   Listen to the previews before deciding.

2. **Lower sample rate.** No code changes: lower `LOW_BUDGET` and the build
   picks a lower rate. Around 5000 Hz speech is still understandable but
   muffled. Memory scales directly with the rate.

3. **Encode pauses inside clips.** About 7.6% of the samples are pauses
   longer than 40 ms inside the clips. Reserve one codeword as an escape:
   `255, n` = "silence for n vectors". This needs a few lines in the
   player. Saves ~7%, and the sound does not change.

4. **Gain-shape (or mean-removed) VQ.** Store a small gain or offset per
   block of vectors, and let the codebook hold only the waveform *shapes*.
   The same 256 entries then cover quiet and loud passages much better.
   That gives better quality at the same size, or allows longer vectors
   (VQ_LEN 6–8) at today's quality. Costs one more lookup or a multiply
   table in the player.

5. **Two-stage VQ.** A second, smaller codebook encodes the error left by
   the first. It trades memory for quality the other way round, so it is
   only useful when combined with longer vectors in stage one.

6. **Smaller program code.** Using the KERNAL `CHROUT`/`GETIN` routines
   directly instead of cc65 conio, and dropping the C runtime pieces that
   are not needed, could save several hundred bytes. The build turns any
   freed bytes into a higher sample rate.

7. **Use the 4 KB RAM under I/O (`$D000–$DFFF`).** To read it, the player
   switches `$01` to `$34` (all RAM), reads a byte, then switches back to
   `$35` to write `$D418`. That costs ~10 cycles per byte. This adds RAM
   rather than saving it: ~4 KB more space. Loading data into it needs a
   copy loop, because the KERNAL LOAD would write to I/O there.

8. **Entropy-code the indices (Huffman).** Codeword use is uneven, so maybe
   ~10% could be saved (an estimate; not measured). Bit-by-bit decoding is
   slow and complex on a 6502, so this is probably not worth it.

9. **Load clips from disk when chosen.** RAM use drops to one clip buffer
   (~3 KB) and any number of clips is possible, even at higher quality.
   The cost is load time: a standard 1541 needs several seconds per clip,
   so a fast loader would be needed for a good experience.

Not worth trying: general-purpose compression (Exomizer, LZ) of the clip
data. VQ indices look nearly random and barely compress. Compressing the
program file would shorten the disk load time, but it saves no RAM.
