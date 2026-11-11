#!/usr/bin/env python3
"""Convert the WAV clips into vector-quantised C64 sample data.

Pipeline per clip:
  trim silence -> resample -> high-pass (DC/rumble) -> treble boost ->
  compressor -> normalise to the 0..15 volume range

All clips are then cut into vectors of VQ_LEN samples and a shared
256-entry codebook is trained (tools/vqenc). Every vector is stored as one
byte, the number of its codeword: VQ_LEN samples per byte.

Silence escape: pauses inside the clips take few bytes. One codeword (ESC,
made of the mid level 8 only) is followed by a count byte n in the data and
means "n vectors of silence". Runs of vectors that hold only the levels 7
and 8 are stored this way, so a pause loses at most its 1-step noise.

The sample rate is fixed (--rate). Only the clips named with --clips are
built. They go into two linker segments:

  * SAMPLES  : inside the main program
  * SAMPLESHI: RAM under the I/O area, $D000-$DFFF (--hi-cap bytes). The
               tool picks the clips that fill it best. The linker writes
               this segment to its own file, which the boot file carries.

Outputs (in the build directory):
  sNN.bin      codeword indices of each clip (NN = original clip number)
  codebook.bin VQ_LEN tables of 256 bytes
  samples.s    ca65 source: codebook, clips, address/length tables
  samples.h    constants for the C program (CLIP_NN = table index)
  vq.inc       constants for the assembler player
  preview/     WAVs of exactly what the C64 plays (for listening on a PC)
"""
import argparse
import array
import math
import os
import subprocess
import wave

SRC_RATE = 12000
SILENCE = 6                          # |s-128| <= this counts as silence
PAL_CLK = 985248
NTSC_CLK = 1022727
K = 256
FILTERS = ("highpass=f=120,"
           "treble=g=5:f=1500,"
           "acompressor=threshold=0.08:ratio=4:attack=5:release=80")


def load_trimmed(path):
    w = wave.open(path)
    assert w.getsampwidth() == 1 and w.getnchannels() == 1
    assert w.getframerate() == SRC_RATE
    d = w.readframes(w.getnframes())
    loud = [i for i, b in enumerate(d) if abs(b - 128) > SILENCE]
    return d[loud[0]:loud[-1] + 1] if loud else d[:1]


def process(raw, rate, vq_len, gain=1.0):
    """Return the clip as floats in 0..15, padded to a multiple of vq_len.

    gain > 1 makes the clip louder: the signal is amplified and the peaks
    are rounded off (tanh), so it still fits the 0..15 range."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "u8", "-ar", str(SRC_RATE), "-ac", "1",
         "-i", "pipe:0",
         "-af", "aresample=%d:filter_size=64:cutoff=0.95,%s" % (rate, FILTERS),
         "-ar", str(rate), "-f", "f32le", "pipe:1"],
        input=raw, stdout=subprocess.PIPE, check=True).stdout
    x = array.array("f", out).tolist()
    # Normalise so that 99.9% of the samples are inside the range.
    peak = sorted(abs(v) for v in x)[int(len(x) * 0.999)] or 1.0
    if gain > 1.0:
        y = [7.5 + 7.5 * math.tanh(gain * v / peak) / math.tanh(gain) for v in x]
    else:
        y = [7.5 + v * 7.5 / peak for v in x]
    y = [min(15.0, max(0.0, v)) for v in y]
    y += [7.5] * (-len(y) % vq_len)
    return y


def best_hi_subset(sizes, cap):
    """Indices whose total size is as large as possible but <= cap."""
    reach = {0: ()}
    for i, s in enumerate(sizes):
        for t, ids in list(reach.items()):
            if t + s <= cap and t + s not in reach:
                reach[t + s] = ids + (i,)
    return set(reach[max(reach)])


def quiet_codewords(codebook, L):
    """Codewords whose samples are all at the mid level (7 or 8)."""
    return [c for c in range(K)
            if all(codebook[j * K + c] in (7, 8) for j in range(L))]


def add_escapes(clip, esc, quiet):
    """Replace runs of quiet vectors by ESC, n pairs."""
    other = [c for c in quiet if c != esc]
    out = bytearray()
    i = 0
    while i < len(clip):
        if clip[i] not in quiet:
            out.append(clip[i])
            i += 1
            continue
        j = i
        while j < len(clip) and clip[j] in quiet:
            j += 1
        n = j - i
        if n == 1 and clip[i] != esc:
            out.append(clip[i])             # a single quiet vector: as it is
        elif n == 1 and other:
            out.append(other[0])            # ESC alone would need two bytes
        else:
            while n:
                out += bytes([esc, min(n, 255)])
                n -= min(n, 255)
        i = j
    return bytes(out)


def decode(clip, codebook, L, esc):
    """The 4-bit samples the C64 player produces."""
    out = []
    i = 0
    while i < len(clip):
        c, n = clip[i], 1
        if c == esc:
            n = clip[i + 1]
            i += 1
        i += 1
        out += [codebook[j * K + c] for j in range(L)] * n
    return out


def write_preview(path, nibbles, rate):
    w = wave.open(path, "wb")
    w.setnchannels(1)
    w.setsampwidth(1)
    w.setframerate(rate)
    w.writeframes(bytes(v * 17 for v in nibbles))
    w.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wavdir")
    ap.add_argument("outdir")
    ap.add_argument("--vqenc", required=True, help="path of the vqenc tool")
    ap.add_argument("--rate", type=int, required=True, help="sample rate in Hz")
    ap.add_argument("--clips", required=True,
                    help="comma separated clip numbers to build, e.g. 1,2,3")
    ap.add_argument("--gain", type=float, default=1.0,
                    help="loudness boost; above 1 the peaks are rounded off")
    ap.add_argument("--hi-cap", type=int, default=4096,
                    help="bytes available under the I/O area")
    ap.add_argument("--vq-len", type=int, default=4,
                    help="samples per byte (vector length)")
    ap.add_argument("--iterations", type=int, default=40)
    args = ap.parse_args()
    L = args.vq_len
    out = args.outdir
    os.makedirs(os.path.join(out, "preview"), exist_ok=True)

    nums = [int(n) for n in args.clips.split(",")]
    files = {int(f[:2]): f for f in os.listdir(args.wavdir)
             if f.lower().endswith(".wav")}
    clips = [load_trimmed(os.path.join(args.wavdir, files[n])) for n in nums]

    rate = args.rate
    data = [process(c, rate, L, args.gain) for c in clips]
    raw_sizes = [len(d) // L for d in data]

    # Train the codebook on all clips and encode them.
    f32 = os.path.join(out, "all.f32")
    with open(f32, "wb") as f:
        for d in data:
            array.array("f", d).tofile(f)
    cbfile = os.path.join(out, "codebook.bin")
    ixfile = os.path.join(out, "indices.bin")
    subprocess.run([args.vqenc, f32, str(L), str(args.iterations), cbfile, ixfile],
                   check=True)
    codebook = open(cbfile, "rb").read()
    indices = open(ixfile, "rb").read()
    os.remove(f32)
    os.remove(ixfile)

    # Silence escape: one quiet codeword becomes ESC and plays the level 8.
    quiet = quiet_codewords(codebook, L)
    if not quiet:
        raise SystemExit("mksamples: no quiet codeword for the silence escape")
    esc = quiet[0]
    codebook = bytearray(codebook)
    for j in range(L):
        codebook[j * K + esc] = 8
    with open(cbfile, "wb") as f:
        f.write(codebook)

    sizes = []
    pos = 0
    for i, n in enumerate(raw_sizes):
        clip = add_escapes(indices[pos:pos + n], esc, quiet)
        pos += n
        nibbles = decode(clip, codebook, L, esc)
        assert len(nibbles) == n * L
        sizes.append(len(clip))
        with open(os.path.join(out, "s%02d.bin" % nums[i]), "wb") as f:
            f.write(clip)
        write_preview(os.path.join(out, "preview", "%02d.wav" % nums[i]), nibbles, rate)
    hiset = best_hi_subset(sizes, args.hi_cap)

    with open(os.path.join(out, "samples.s"), "w") as f:
        f.write("; generated by tools/mksamples.py - do not edit\n")
        f.write(".export _sample_addr, _sample_len, _codebook\n\n")
        f.write('.segment "CODEBOOK"\n')
        f.write('_codebook: .incbin "%s"\n' % cbfile)
        for seg, want_hi in (("SAMPLES", False), ("SAMPLESHI", True)):
            f.write('\n.segment "%s"\n' % seg)
            for i in range(len(sizes)):
                if (i in hiset) == want_hi:
                    f.write('smp%02d: .incbin "%s/s%02d.bin"\n' % (nums[i], out, nums[i]))
        f.write('\n.segment "RODATA"\n')
        f.write("_sample_addr: .word %s\n" % ", ".join("smp%02d" % n for n in nums))
        f.write("_sample_len:  .word %s\n" % ", ".join(map(str, sizes)))

    with open(os.path.join(out, "vq.inc"), "w") as f:
        f.write("; generated by tools/mksamples.py - do not edit\n")
        f.write("VQ_LEN = %d\n" % L)
        f.write("LATCH_PAL = %d\n" % (round(PAL_CLK / rate) - 1))
        f.write("VQ_ESC = %d\n" % esc)

    with open(os.path.join(out, "samples.h"), "w") as f:
        f.write("/* generated by tools/mksamples.py - do not edit */\n")
        f.write("#define NUM_SAMPLES %d\n" % len(sizes))
        f.write("#define SAMPLE_RATE %d\n" % rate)
        f.write("#define LATCH_PAL   %d\n" % (round(PAL_CLK / rate) - 1))
        f.write("#define LATCH_NTSC  %d\n" % (round(NTSC_CLK / rate) - 1))
        for i, n in enumerate(nums):
            f.write("#define CLIP_%02d     %d\n" % (n, i))

    hi = sum(s for i, s in enumerate(sizes) if i in hiset)
    print("mksamples: %d Hz, %d samples/byte, codebook %d, clips %d bytes "
          "(%d before the silence escape), of which %d under I/O (clips %s)"
          % (rate, L, L * K, sum(sizes), sum(raw_sizes), hi,
             ", ".join(str(nums[i]) for i in sorted(hiset))))


if __name__ == "__main__":
    main()
