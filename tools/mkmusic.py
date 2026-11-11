#!/usr/bin/env python3
"""Cut the GoatTracker player and song out of a PSID file.

The game calls init at $1000 (A = 0) and play at $1003 once per frame, so
only the bytes from $1000 on are kept. Anything before $1000 (the timer
wrapper of the .sid) is dropped.

With a volume argument (0-15) the master volume of the player is patched:
the player sets $D418 at every call with  ORA #$0F / STA $D418.

usage: mkmusic.py song.sid music.bin [volume]
"""
import struct
import sys

BASE = 0x1000
MAX_SIZE = 0x05BA          # size of the MUSIC area in src/inva64.cfg


def main():
    src, dst = sys.argv[1:3]
    d = open(src, "rb").read()
    if d[0:4] != b"PSID":
        sys.exit("mkmusic: %s is not a PSID file" % src)
    data_off, load, init, play = struct.unpack(">HHHH", d[6:14])
    body = d[data_off:]
    if load == 0:
        load = body[0] | body[1] << 8
        body = body[2:]
    if play != BASE + 3:
        sys.exit("mkmusic: play address is $%04X, expected $%04X" % (play, BASE + 3))
    if not load <= BASE < load + len(body):
        sys.exit("mkmusic: data at $%04X does not cover $%04X" % (load, BASE))
    body = body[BASE - load:]
    if len(body) > MAX_SIZE:
        sys.exit("mkmusic: music is %d bytes, the MUSIC area is %d" % (len(body), MAX_SIZE))
    if len(sys.argv) > 3:
        vol = int(sys.argv[3])
        pat = bytes([0x09, 0x0F, 0x8D, 0x18, 0xD4])
        if not 0 <= vol <= 15 or body.count(pat) != 1:
            sys.exit("mkmusic: cannot set the volume (pattern not found or bad value)")
        body = body.replace(pat, bytes([0x09, vol]) + pat[2:])
    open(dst, "wb").write(body)
    print("mkmusic: %d bytes at $%04X" % (len(body), BASE))


if __name__ == "__main__":
    main()
