#!/usr/bin/env python3
"""Print the free bytes of each memory area from an ld65 map file.

usage: memreport.py main.map
"""
import re
import sys

# area name -> (start, size, segments placed in it), as in src/inva64.cfg
AREAS = [
    ("ONESHOT", 0x0400, 0x0400, ["ONESHOT"]),
    ("LOW",     0x0800, 0x0800, ["STARTUP", "CODEBOOK", "RODATA", "DATA",
                                 "INIT", "ONCE", "LOWCODE"]),
    ("MUSIC",   0x1000, 0x05BA, ["MUSIC"]),
    ("MAIN",    0x15BA, 0xCC00 - 0x15BA - 0x100, ["CODE", "SAMPLES", "BSS"]),
    ("HIRAM",   0xD000, 0x1000, ["SAMPLESHI"]),
]


def main():
    sizes = {}
    in_list = False
    for line in open(sys.argv[1]):
        if line.startswith("Segment list"):
            in_list = True
        elif in_list:
            m = re.match(r"(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})", line)
            if m:
                sizes[m.group(1)] = int(m.group(4), 16)
            elif line.startswith("Exports"):
                break
    print("memory use:")
    for name, start, size, segs in AREAS:
        used = sum(sizes.get(s, 0) for s in segs)
        detail = ", ".join("%s %d" % (s, sizes[s]) for s in segs if sizes.get(s))
        print("  %-8s $%04X  %5d of %5d used, %5d free  (%s)"
              % (name, start, used, size, size - used, detail))


if __name__ == "__main__":
    main()
