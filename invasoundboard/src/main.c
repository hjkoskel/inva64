/*
 * C64 sound board: type a clip number and press RETURN to play it.
 *
 * Samples are vector quantised (see play.s). Most live inside the program,
 * the rest in the RAM under the KERNAL ($E000-), loaded from a second file
 * at start-up. Playback itself is in play.s.
 */
#include <conio.h>
#include <c64.h>
#include <cbm.h>
#include <device.h>
#include "samples.h"

extern const unsigned char *const sample_addr[NUM_SAMPLES];
extern const unsigned int sample_len[NUM_SAMPLES];

extern const unsigned char *play_ptr;
extern unsigned int play_len;
extern unsigned int play_latch;
void play_init(void);
void play(void);

#define HI_FILE "hisamples"
#define STR(x)  #x
#define XSTR(x) STR(x)

/* Read a number of up to two digits; RETURN accepts, DEL edits. */
static unsigned char read_number(void)
{
    unsigned char digits[2];
    unsigned char n = 0;
    char c;

    cursor(1);
    for (;;) {
        c = cgetc();
        if (c >= '0' && c <= '9' && n < 2) {
            cputc(c);
            digits[n++] = c - '0';
        } else if (c == CH_DEL && n) {
            --n;
            gotox(wherex() - 1);
            cputc(' ');
            gotox(wherex() - 1);
        } else if (c == CH_ENTER && n) {
            break;
        }
    }
    cursor(0);
    return n == 1 ? digits[0] : digits[0] * 10 + digits[1];
}

int main(void)
{
    unsigned char nr;
#if HI_SIZE > 0
    unsigned char dev, hi_ok;
#endif

    bordercolor(COLOR_BLACK);
    bgcolor(COLOR_BLACK);
    textcolor(COLOR_LIGHTGREEN);
    clrscr();
    cputs("C64 SOUND BOARD\r\n\r\n");

#if HI_SIZE > 0
    cputs("loading samples...\r\n");
    dev = getcurrentdevice();
    if (dev < 8) {
        dev = 8;
    }
    hi_ok = cbm_load(HI_FILE, dev, (void *)HI_START) == HI_SIZE;
    if (!hi_ok) {
        /* Keep going: only the clips stored in that file are missing. */
        cputs("file " HI_FILE " not found!\r\n"
              "run from soundboard.d64 to get\r\n"
              "all clips.\r\n");
    }
#endif

    play_init();
    play_latch = get_tv() == TV_NTSC ? LATCH_NTSC : LATCH_PAL;

    cputs("enter 1-" XSTR(NUM_SAMPLES) ", then return\r\n\r\n");
    for (;;) {
        cputs("sample? ");
        nr = read_number();
        if (nr < 1 || nr > NUM_SAMPLES) {
            cputs("  no such sample\r\n");
#if HI_SIZE > 0
        } else if (!hi_ok && sample_addr[nr - 1] >= (const unsigned char *)HI_START) {
            cputs("  not loaded\r\n");
#endif
        } else {
            cputs("  playing\r\n");
            play_ptr = sample_addr[nr - 1];
            play_len = sample_len[nr - 1];
            play();
        }
    }
}
