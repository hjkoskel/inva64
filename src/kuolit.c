/*
 * Game over screen: "KUOLIT" and the money gained.
 *
 * Text mode in VIC bank 0 with the screen at $0400, because the character
 * ROM is not visible in bank 3. The map bitmap stays in memory.
 */
#include <string.h>
#include "game.h"

#define TEXT 0x0400

/* Write a string as screen codes. */
static void __fastcall__ put(unsigned char *at, const char *s)
{
    while (*s) {
        *at = *s & 0x3F;
        ++at;
        ++s;
    }
}

void kuolit(void)
{
    POKE(0xD015, 0);                    /* cursor off */
    POKE(0xD011, 0x0B);                 /* screen off */
    memset((void *)TEXT, 0x20, 1000);
    memset((void *)0xD800, 1, 1000);    /* white text */
    put((unsigned char *)TEXT + 9 * 40 + 17, "KUOLIT");
    put((unsigned char *)TEXT + 12 * 40 + 14, "RAHAA:");
    money_digits();
    memcpy((void *)(TEXT + 12 * 40 + 21), digits, 5);

    POKE(0xD021, 0);
    POKE(0xDD00, PEEK(0xDD00) | 0x03);  /* VIC bank 0 */
    POKE(0xD018, 0x15);                 /* screen $0400, upper case set */
    POKE(0xD016, 0x08);
    POKE(0xD011, 0x1B);                 /* text mode, screen on */

    while (input_any()) {               /* wait for release, press, release */
        wait_frame();
    }
    while (!input_any()) {
        wait_frame();
    }
    while (input_any()) {
        wait_frame();
    }
}
