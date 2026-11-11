# Invataxi for the Commodore 64.
# Needs cc65, python3, ffmpeg, a host C compiler and VICE (c1541, x64sc).
#
#   make        build inva64.d64
#   make run    start it in VICE
#   make test   play it in VICE through the remote monitor and check the rules
#   make clean

BUILD   := build
SMP     := $(BUILD)/smp
VQENC   := $(BUILD)/vqenc
WAVDIR  := invasoundboard/wav

# Sound quality: the same as in the soundboard.
RATE    := 6594
VQ_LEN  := 5
# Music master volume, 0-15. The samples are quieter than the music at 15.
MUSIC_VOLUME := 10
# Loudness boost of the clips. 1 = none (as in the soundboard). Above 1 the
# clips get louder and their peaks are rounded off; they also take a little
# more memory, because pauses are less often pure silence.
CLIP_GAIN := 1.5
# Clips in the game (4, 9 and 15 are left out).
CLIPS   := 1,2,3,5,6,7,8,10,11,12,13,14,16,17,18,19,20,21,22,23,24
# Bytes of clip data for the RAM under I/O ($D000-$DFFF).
HI_CAP  := 4096

CFLAGS  := -t c64 -Oirs --static-locals -I src -I $(SMP)
C_SRC   := src/main.c src/game.c src/playfield.c src/input.c src/kuolit.c
S_SRC   := src/crt0.s src/irq.s src/play.s src/data.s
GFX     := $(BUILD)/title_bmp.bin $(BUILD)/title_scr.bin $(BUILD)/title_col.bin \
           $(BUILD)/title.inc $(BUILD)/map_bmp.z $(BUILD)/map_scr.z $(BUILD)/cursor.bin
SAMPLES := $(SMP)/samples.s $(SMP)/samples.h $(SMP)/vq.inc
OBJS    := $(C_SRC:src/%.c=$(BUILD)/%.o) $(S_SRC:src/%.s=$(BUILD)/%.o) $(BUILD)/samples.o

all: inva64.d64

$(BUILD):
	mkdir -p $(BUILD)

$(VQENC): tools/vqenc.c | $(BUILD)
	$(CC) -O2 -o $@ $< -lm

$(GFX) &: tools/mkgfx.py invatitle.kla kartta/kartta_hires.art | $(BUILD)
	python3 tools/mkgfx.py invatitle.kla kartta/kartta_hires.art $(BUILD)

$(BUILD)/music.bin: tools/mkmusic.py harmonia_small.sid Makefile | $(BUILD)
	python3 tools/mkmusic.py harmonia_small.sid $@ $(MUSIC_VOLUME)

$(SAMPLES) &: tools/mksamples.py $(VQENC) $(wildcard $(WAVDIR)/*.wav) Makefile
	python3 tools/mksamples.py $(WAVDIR) $(SMP) --vqenc $(VQENC) \
	        --rate $(RATE) --vq-len $(VQ_LEN) --clips $(CLIPS) --hi-cap $(HI_CAP) --gain $(CLIP_GAIN)

$(BUILD)/%.o: src/%.c src/game.h src/config.h $(SMP)/samples.h
	cl65 -c $(CFLAGS) -o $@ $<

$(BUILD)/%.o: src/%.s $(SMP)/vq.inc $(GFX) $(BUILD)/music.bin
	ca65 -t c64 -I $(SMP) -o $@ $<

$(BUILD)/samples.o: $(SMP)/samples.s
	ca65 -t c64 -o $@ $<

# Main game file. The linker also writes build/hi.bin (clips for $D000).
$(BUILD)/main.prg $(BUILD)/hi.bin &: $(OBJS) src/inva64.cfg
	ld65 -C src/inva64.cfg -m $(BUILD)/main.map -Ln $(BUILD)/main.lbl \
	     -o $(BUILD)/main.prg $(OBJS) c64.lib
	@python3 tools/memreport.py $(BUILD)/main.map

# Boot file: title picture, clips for $D000, loader.
$(BUILD)/boot.prg: src/boot.s src/boot.cfg $(GFX) $(BUILD)/hi.bin
	cl65 -t none -C src/boot.cfg --asm-include-dir $(BUILD) \
	     -o $@ src/boot.s
	rm -f src/boot.o

inva64.d64: $(BUILD)/boot.prg $(BUILD)/main.prg
	rm -f $@
	c1541 -format "invataxi,64" d64 $@ \
	      -write $(BUILD)/boot.prg invataxi \
	      -write $(BUILD)/main.prg main >/dev/null

run: inva64.d64
	x64sc -autostart inva64.d64

test: inva64.d64
	python3 tests/playtest.py

clean:
	rm -rf $(BUILD) inva64.d64

.PHONY: all run test clean
