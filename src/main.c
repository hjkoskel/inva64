/*
 * Invataxi for the Commodore 64 - start-up and intro.
 *
 * The boot file has put the title picture on screen and loaded this
 * program. The music starts, the title shows "READY", and a key or the
 * fire button starts the game. The intro code is in the ONESHOT segment ($0400-$07FF), which
 * becomes the text screen of the KUOLIT screen later.
 */
#include <string.h>
#include <6502.h>
#include "game.h"

#pragma code-name (push, "ONESHOT")

#define SPRITES    0xFF40           /* later the cursor sprites */
#define SPRITE_PTR 0xFD
#define SCREEN     0xCC00

/* Show "READY" on the title picture and wait for a key or the fire button.
   The text is two double-size sprites, built from the character ROM, with
   two black copies behind them as a shadow. (In the main code area: the
   one-shot zone is full.) */
#pragma code-name (pop)
static void ready(void)
{
    static const unsigned char text[5] = { 18, 5, 1, 4, 25 };   /* READY */
    static unsigned char c, row;
    static unsigned char *src, *dst;

    memset((void *)SPRITES, 0, 128);
    SEI();
    POKE(0x01, 0x32);                   /* character ROM in place of I/O */
    for (c = 0; c < 5; ++c) {
        src = (unsigned char *)0xD000 + ((unsigned int)text[c] << 3);
        dst = (unsigned char *)SPRITES + (c < 3 ? c : c + 61);
        for (row = 0; row < 8; ++row) {
            *dst = src[row];
            dst += 3;
        }
    }
    POKE(0x01, 0x36);
    CLI();

    for (c = 0; c < 4; ++c) {
        POKE(SCREEN + 0x3F8 + c, SPRITE_PTR + (c & 1));
        POKE(0xD027 + c, c < 2 ? 1 : 0);                /* white, shadow black */
        POKE(0xD000 + 2 * c, READY_X + 24 + (c & 1) * 48 + (c & 2));
        POKE(0xD001 + 2 * c, READY_Y + 50 + (c & 2));
    }
    POKE(0xD010, 0);
    POKE(0xD017, 0x0F);                 /* double height and width */
    POKE(0xD01D, 0x0F);
    POKE(0xD01B, 0);
    POKE(0xD01C, 0);

    while (input_any()) {               /* a key may still be down from LOAD */
        wait_frame();
    }
    while (!input_any()) {
        wait_frame();
        POKE(0xD015, (frame & READY_BLINK_MASK) ? 0x00 : 0x0F);
    }
    POKE(0xD015, 0);
}
#pragma code-name (push, "ONESHOT")

static void intro(void)
{
    POKE(0xDC02, 0xFF);                 /* keyboard matrix: port A out, B in */
    POKE(0xDC03, 0x00);

    irq_init();                         /* the music starts here */
    ready();

    /* Random seed: CIA timer and raster line at the moment of the key
       press, and the KERNAL clock, which depends on the disk load time. */
    seed = PEEK(0xDC04) ^ PEEK(0xD012) ^ ((unsigned int)PEEK(0xA2) << 8);

    pause(INTRO_WAIT_FRAMES);
    say(CLIP_01);                       /* "millä kotiin" */
    pause(INTRO_GAP_FRAMES);
    say(CLIP_03);                       /* "invataxilla" */
    pause(MAP_PAUSE_FRAMES);
    playfield_show();
}

#pragma code-name (pop)

void main(void)
{
    intro();
    game_run();
}
