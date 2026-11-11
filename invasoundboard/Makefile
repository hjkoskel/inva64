# C64 sound board - needs cc65, python3, ffmpeg, a host C compiler and
# c1541 (VICE)
#
# Outputs:
#   soundboard.prg     main version: one self-contained file
#   soundboard-hq.prg  alternative: higher sample rate, needs the file
#                      "hisamples" (RAM under the KERNAL) from the same disk
#   soundboard.d64     disk with both: "soundboard" (first, autostarts),
#                      "soundboard hq" and "hisamples"
#
# LOW_BUDGET = bytes of codebook + sample data kept inside the program.
#              Raise it until the linker complains (higher -> higher rate).
# VQ_LEN     = samples per byte (vector length): 4 = cleaner, 5 = default,
#              6 or 8 = less memory per second, grainier sound.

LOW_BUDGET ?= 49000
VQ_LEN     ?= 5
BUILD      := build
VQENC      := $(BUILD)/vqenc
SAMPLEOPTS  = --vqenc $(VQENC) --low-budget $(LOW_BUDGET) --vq-len $(VQ_LEN)
CL65OPTS    = -t c64 -O -C src/soundboard.cfg
SOURCES     = src/main.c src/play.s src/soundboard.cfg

all: soundboard.prg soundboard.d64

$(VQENC): tools/vqenc.c
	@mkdir -p $(BUILD)
	$(CC) -O2 -o $@ $< -lm

# --- sample data: single file (all clips in the program) ---------------------
$(BUILD)/single/samples.s $(BUILD)/single/samples.h $(BUILD)/single/vq.inc &: tools/mksamples.py $(VQENC) $(wildcard wav/*.wav) Makefile
	python3 tools/mksamples.py wav $(BUILD)/single $(SAMPLEOPTS) --hi-cap 0

# --- sample data: hq (program + "hisamples" under the KERNAL) ----------------
$(BUILD)/hq/samples.s $(BUILD)/hq/samples.h $(BUILD)/hq/vq.inc $(BUILD)/hq/hi.prg &: tools/mksamples.py $(VQENC) $(wildcard wav/*.wav) Makefile
	python3 tools/mksamples.py wav $(BUILD)/hq $(SAMPLEOPTS)

# --- programs -----------------------------------------------------------------
soundboard.prg: $(SOURCES) $(BUILD)/single/samples.s $(BUILD)/single/samples.h $(BUILD)/single/vq.inc
	cl65 $(CL65OPTS) -I $(BUILD)/single --asm-include-dir $(BUILD)/single \
	     -m $(BUILD)/single/soundboard.map -o $@ src/main.c src/play.s $(BUILD)/single/samples.s
	rm -f src/*.o

soundboard-hq.prg: $(SOURCES) $(BUILD)/hq/samples.s $(BUILD)/hq/samples.h $(BUILD)/hq/vq.inc
	cl65 $(CL65OPTS) -I $(BUILD)/hq --asm-include-dir $(BUILD)/hq \
	     -m $(BUILD)/hq/soundboard.map -o $@ src/main.c src/play.s $(BUILD)/hq/samples.s
	rm -f src/*.o

soundboard.d64: soundboard.prg soundboard-hq.prg $(BUILD)/hq/hi.prg
	rm -f $@
	c1541 -format "soundboard,sb" d64 $@ \
	      -write soundboard.prg soundboard \
	      -write soundboard-hq.prg "soundboard hq" \
	      -write $(BUILD)/hq/hi.prg hisamples >/dev/null

run: soundboard.prg
	x64sc -autostart soundboard.prg

run-d64: soundboard.d64
	x64sc -autostart soundboard.d64

clean:
	rm -rf $(BUILD) build-single soundboard.prg soundboard-hq.prg \
	       soundboard.d64 soundboard-single.prg src/*.o

.PHONY: all run run-d64 clean
