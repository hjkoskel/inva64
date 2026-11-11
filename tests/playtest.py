#!/usr/bin/env python3
"""Play the game in VICE through the remote monitor and check the rules.

The test runs the real disk image in warp mode. It finds addresses in
build/main.lbl, stops the game at known points with breakpoints, moves the
cursor by writing its variables, and "presses fire" by patching
input_read() for one call.

usage: playtest.py [output directory for screenshots]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from vicemon import Vice, labels

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "test"))
os.makedirs(OUT, exist_ok=True)
L = labels(os.path.join(ROOT, "build", "main.lbl"))

# Click areas, as in src/playfield.c: x, y, w, h. Index = place number.
AREAS = [(80, 108, 48, 28), (254, 136, 50, 44), (202, 99, 36, 29), (8, 48, 56, 49),
         (206, 144, 24, 26), (136, 64, 96, 35), (2, 104, 30, 35), (8, 139, 70, 53),
         (80, 0, 72, 24), (248, 0, 72, 64), (120, 160, 48, 23), (160, 0, 56, 46),
         (76, 69, 44, 27), (248, 88, 56, 33)]
KIRPPUTORI = 13
EMPTY = (240, 75)                       # a point outside every area

v = Vice(os.path.join(ROOT, "inva64.d64"), ["-sounddev", "dummy"])
failures = 0


def check(what, got, want):
    global failures
    ok = got == want
    failures += not ok
    print("%-4s %s: %r%s" % ("ok" if ok else "FAIL", what, got, "" if ok else " (expected %r)" % (want,)))


def until_exec(name):
    v.cmd("delete")
    v.cmd("break %04x" % L[name])
    v.go()


def until_store(name):
    v.cmd("delete")
    v.cmd("watch store %04x" % L[name])
    v.go()


def state():
    m = v.peek(L["_money"], 2)
    lives = v.peek(L["_lives"])[0]
    return m[0] | m[1] << 8, lives - 256 if lives > 127 else lives


def shot(name):
    v.cmd('screenshot "%s" 2' % os.path.join(OUT, name))


def next_round():
    """Run to the point where the round waits for the answer."""
    until_store("_last_place")
    until_exec("_digi_end")
    return v.peek(L["_last_place"])[0]


def click(x, y):
    """Put the cursor at x, y and press fire; returns the place that was hit."""
    v.poke(L["_cursor_x"], [x & 255, x >> 8])
    v.poke(L["_cursor_y"], [y])
    old = v.peek(L["_input_read"], 5)
    v.poke(L["_input_read"], [0xA2, 0x00, 0xA9, 0x10, 0x60])    # return IN_FIRE
    until_exec("_playfield_hit")
    v.poke(L["_input_read"], old)
    v.cmd("delete")


def centre(place):
    x, y, w, h = AREAS[place]
    return x + w // 2, y + h // 2


def wrong_place(place):
    return (place + 1) % 13


# Title: the music plays and READY blinks until a key or fire is pressed.
until_exec("_irq_init")
v.cmd("delete")
for i in range(40):                     # catch the blinking text when it is on
    v.run_free()
    time.sleep(0.3)
    v.stop()
    if v.peek(0xD015)[0] & 0x0F:
        break
check("READY text is shown", v.peek(0xD015)[0] & 0x0F, 0x0F)
shot("1_title.png")
check("game waits for a key", v.peek(L["_last_place"])[0], 0xFF)
old = v.peek(L["_input_any"], 5)
v.poke(L["_input_any"], [0xA2, 0x00, 0xA9, 0x01, 0x60])         # a key is down
until_exec("_playfield_show")
v.poke(L["_input_any"], old)

place = next_round()
check("start: money, lives", state(), (0, 3))
shot("2_map.png")

click(*centre(place))
place = next_round()
check("right place", state(), (15, 3))

click(*EMPTY)                           # ignored, then the time runs out
place = next_round()
check("empty ground, then timeout", state(), (0, 3))

place = next_round()                    # no click at all
check("timeout at 0 money stays 0", state(), (0, 3))

for want in (15, 30, 45):
    click(*centre(place))
    place = next_round()
    check("right place", state(), (want, 3))
shot("3_money.png")

place = next_round()
check("timeout takes 15", state(), (30, 3))

click(*centre(KIRPPUTORI))
place = next_round()
check("KIRPPUTORI is wrong", state(), (30, 2))
shot("4_lives.png")

for want in (1, 0):
    click(*centre(wrong_place(place)))
    place = next_round()
    check("wrong place", state(), (30, want))

click(*centre(wrong_place(place)))
until_exec("_kuolit")
check("lives below 0 ends the game", state(), (30, -1))
v.cmd("delete")
v.run_free()
time.sleep(1.5)
v.stop()
shot("5_kuolit.png")

old = v.peek(L["_input_any"], 5)
v.poke(L["_input_any"], [0xA2, 0x00, 0xA9, 0x01, 0x60])         # a key is down
v.run_free()
time.sleep(1.0)
v.stop()
v.poke(L["_input_any"], old)                                     # ... and up again
place = next_round()
check("new game after KUOLIT", state(), (0, 3))
shot("6_again.png")

v.quit()
print("FAILED: %d" % failures if failures else "all checks passed")
sys.exit(1 if failures else 0)
