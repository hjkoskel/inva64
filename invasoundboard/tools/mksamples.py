#!/usr/bin/env python3
"""Convert the WAV clips into vector-quantised C64 sample data.

Pipeline per clip:
  trim silence -> resample -> high-pass (DC/rumble) -> treble boost ->
  compressor -> normalise to the 0..15 volume range

All clips are then cut into vectors of VQ_LEN samples and a shared
256-entry codebook is trained (tools/vqenc). Every vector is stored as one
byte, the number of its codeword: VQ_LEN samples per byte.

The sample rate is chosen automatically: the highest rate at which the
codebook and all clips fit into the RAM that is available on the C64:

  * LOW area : part of the main program ($0801-$CFFF minus code/stack),
               holds the codebook and most clips
  * HIGH area: RAM under the KERNAL ROM, $E000-$FFF9, loaded as a separate
               file at start-up (the CPU vectors at $FFFA- are left alone)

Outputs (in the build directory):
  sNN.bin      codeword indices of each clip
  codebook.bin VQ_LEN tables of 256 bytes
  samples.s    ca65 source: codebook, LOW clips, address/length tables
  samples.h    constants for the C program
  vq.inc       constants for the assembler player
  hi.prg       HIGH area contents with $E000 load address
  preview/     WAVs of exactly what the C64 plays (for listening on a PC)
"""
import argparse
import array
import os
import subprocess
import wave

SRC_RATE = 12000
HI_START = 0xE000
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


def process(raw, rate, vq_len):
    """Return the clip as floats in 0..15, padded to a multiple of vq_len."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "u8", "-ar", str(SRC_RATE), "-ac", "1",
         "-i", "pipe:0",
         "-af", "aresample=%d:filter_size=64:cutoff=0.95,%s" % (rate, FILTERS),
         "-ar", str(rate), "-f", "f32le", "pipe:1"],
        input=raw, stdout=subprocess.PIPE, check=True).stdout
    x = array.array("f", out).tolist()
    # Normalise so that 99.9% of the samples are inside the range.
    peak = sorted(abs(v) for v in x)[int(len(x) * 0.999)] or 1.0
    y = [min(15.0, max(0.0, 7.5 + v * 7.5 / peak)) for v in x]
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


def fits(sizes, args):
    hi = best_hi_subset(sizes, args.hi_cap)
    low = sum(s for i, s in enumerate(sizes) if i not in hi)
    return low + args.vq_len * K <= args.low_budget, hi


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
    ap.add_argument("--low-budget", type=int, default=49000,
                    help="bytes for codebook + clips inside the program")
    ap.add_argument("--hi-cap", type=int, default=0xFFFA - HI_START,
                    help="bytes under the KERNAL (0 = single file build)")
    ap.add_argument("--vq-len", type=int, default=4,
                    help="samples per byte (vector length)")
    ap.add_argument("--iterations", type=int, default=40)
    args = ap.parse_args()
    L = args.vq_len
    out = args.outdir
    os.makedirs(os.path.join(out, "preview"), exist_ok=True)

    files = sorted(f for f in os.listdir(args.wavdir) if f.lower().endswith(".wav"))
    clips = [load_trimmed(os.path.join(args.wavdir, f)) for f in files]

    # Estimate the highest rate that fits, then verify with real data.
    est = lambda r: [-(-(len(c) * r // SRC_RATE + 2) // L) for c in clips]
    lo, hi_r = 1000, SRC_RATE
    while lo < hi_r:
        mid = (lo + hi_r + 1) // 2
        if fits(est(mid), args)[0]:
            lo = mid
        else:
            hi_r = mid - 1
    rate = lo
    while True:
        data = [process(c, rate, L) for c in clips]
        sizes = [len(d) // L for d in data]
        ok, hiset = fits(sizes, args)
        if ok:
            break
        rate -= 25

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

    hi_img = bytearray()
    addr_expr = []
    pos = 0
    for i, n in enumerate(sizes):
        clip = indices[pos:pos + n]
        pos += n
        with open(os.path.join(out, "s%02d.bin" % (i + 1)), "wb") as f:
            f.write(clip)
        write_preview(os.path.join(out, "preview", "%02d.wav" % (i + 1)),
                      [codebook[j * K + c] for c in clip for j in range(L)], rate)
        if i in hiset:
            addr_expr.append("$%04X" % (HI_START + len(hi_img)))
            hi_img += clip
        else:
            addr_expr.append("smp%02d" % (i + 1))
    with open(os.path.join(out, "hi.prg"), "wb") as f:
        f.write(bytes([HI_START & 0xFF, HI_START >> 8]) + hi_img)

    with open(os.path.join(out, "samples.s"), "w") as f:
        f.write("; generated by tools/mksamples.py - do not edit\n")
        f.write(".export _sample_addr, _sample_len, _codebook\n\n")
        f.write('.segment "SAMPLES"\n')
        f.write('_codebook: .incbin "%s"\n' % cbfile)
        for i in range(len(sizes)):
            if i not in hiset:
                f.write('smp%02d: .incbin "%s/s%02d.bin"\n' % (i + 1, out, i + 1))
        f.write('\n.segment "RODATA"\n')
        f.write("_sample_addr: .word %s\n" % ", ".join(addr_expr))
        f.write("_sample_len:  .word %s\n" % ", ".join(map(str, sizes)))

    with open(os.path.join(out, "vq.inc"), "w") as f:
        f.write("; generated by tools/mksamples.py - do not edit\n")
        f.write("VQ_LEN = %d\n" % L)

    with open(os.path.join(out, "samples.h"), "w") as f:
        f.write("/* generated by tools/mksamples.py - do not edit */\n")
        f.write("#define NUM_SAMPLES %d\n" % len(sizes))
        f.write("#define SAMPLE_RATE %d\n" % rate)
        f.write("#define LATCH_PAL   %d\n" % (round(PAL_CLK / rate) - 1))
        f.write("#define LATCH_NTSC  %d\n" % (round(NTSC_CLK / rate) - 1))
        f.write("#define HI_START    0x%04X\n" % HI_START)
        f.write("#define HI_SIZE     %d\n" % len(hi_img))

    low = sum(s for i, s in enumerate(sizes) if i not in hiset)
    print("rate %d Hz, %d samples/byte, low %d+%d bytes (budget %d), "
          "high %d bytes (clips %s)"
          % (rate, L, L * K, low, args.low_budget, len(hi_img),
             ", ".join(str(i + 1) for i in sorted(hiset))))


if __name__ == "__main__":
    main()
