/*
 * Playfield: the hires map, the money and lives display, the click areas.
 *
 * VIC bank 3: bitmap at $E000 (RAM under the KERNAL), screen RAM at $CC00,
 * cursor sprites at $FF40 and $FF80 (above the bitmap).
 */
#include <zlib.h>
#include <6502.h>
#include "game.h"

#define BITMAP     0xE000
#define SCREEN     0xCC00
#define SPRITES    0xFF40
#define SPRITE_PTR 0xFD             /* (0xFF40 - 0xC000) / 64 */

#define HUD_ROW_BMP (BITMAP + 24 * 40 * 8)  /* bitmap of the bottom row */
#define HUD_ROW_SCR (SCREEN + 24 * 40)      /* its colours */
#define MONEY_COL  7                /* after the "MONEY" label */
#define LIVES_COL  23               /* below the "EMÄLÄT" sign */

unsigned char digits[5];

typedef struct {
    unsigned int x;
    unsigned char y, w, h;
} area_t;

/* Click areas in map pixels. The index is the place number. */
static const area_t areas[NUM_AREAS] = {
    {  80, 108, 48, 28 },   /* UIMAHALLI */
    { 254, 136, 50, 44 },   /* DRUGS */
    { 202,  99, 36, 29 },   /* MAKKARI */
    {   8,  48, 56, 49 },   /* KUKKIA */
    { 206, 144, 24, 26 },   /* RKIOSKI */
    { 136,  64, 96, 35 },   /* SORSAPUISTO */
    {   2, 104, 30, 35 },   /* WC */
    {   8, 139, 70, 53 },   /* ANKKALINNA */
    {  80,   0, 72, 24 },   /* KIRJASTO */
    { 248,   0, 72, 64 },   /* SAIRAALA */
    { 120, 160, 48, 23 },   /* POLIS */
    { 160,   0, 56, 46 },   /* RAUTAA */
    {  76,  69, 44, 27 },   /* SIWA */
    { 248,  88, 56, 33 }    /* KIRPPUTORI: never asked for, always wrong */
};

/* Place under the cursor, or -1. */
signed char playfield_hit(void)
{
    unsigned char i;
    const area_t *a = areas;

    for (i = 0; i < NUM_AREAS; ++i, ++a) {
        if (cursor_x - a->x < a->w && (unsigned char)(cursor_y - a->y) < a->h) {
            return i;
        }
    }
    return -1;
}

/* Copy one character from the character ROM into the bottom bitmap row. */
static void __fastcall__ glyph(unsigned char col, unsigned char code)
{
    static unsigned char *src, *dst;
    static unsigned char i;

    src = (unsigned char *)0xD000 + ((unsigned int)code << 3);
    dst = (unsigned char *)HUD_ROW_BMP + ((unsigned int)col << 3);
    SEI();
    POKE(0x01, 0x32);               /* character ROM in place of I/O */
    for (i = 0; i < 8; ++i) {
        dst[i] = src[i];
    }
    POKE(0x01, 0x36);
    CLI();
}

/* Money as 5 screen codes in digits[]. */
void money_digits(void)
{
    static const unsigned int pow10[4] = { 10000, 1000, 100, 10 };
    unsigned int v = money;
    unsigned char i, d;

    for (i = 0; i < 4; ++i) {
        d = '0';
        while (v >= pow10[i]) {
            v -= pow10[i];
            ++d;
        }
        digits[i] = d;
    }
    digits[4] = '0' + (unsigned char)v;
}

void hud_money(void)
{
    unsigned char i;

    money_digits();
    for (i = 0; i < 5; ++i) {
        glyph(MONEY_COL + i, digits[i]);
    }
}

/* One heart for each life left. */
void hud_lives(void)
{
    unsigned char i;

    for (i = 0; i < START_LIVES; ++i) {
        glyph(LIVES_COL + i, (signed char)i < lives ? 0x53 : 0x20);
    }
}

/* Switch to the map (again) and draw the money and the lives. */
void playfield_on(void)
{
    hud_money();
    hud_lives();
    POKE(0xDD00, PEEK(0xDD00) & 0xFC);  /* VIC bank 3 */
    POKE(0xD018, 0x38);                 /* screen $CC00, bitmap $E000 */
    POKE(0xD016, 0x08);                 /* hires */
    POKE(0xD011, 0x3B);                 /* bitmap mode, screen on */
    POKE(0xD015, 0x03);                 /* cursor sprites on */
}

#pragma code-name (push, "ONESHOT")

/* Unpack the map over the title picture. Runs once: the bitmap stays in
   memory during the KUOLIT screen. */
void playfield_show(void)
{
    unsigned char i;

    POKE(0xD011, 0x2B);                 /* screen off while unpacking */

    /* The unpacker reads back what it has written, so the KERNAL ROM must
       be out of the way while it writes to $E000-. The frame interrupt
       works without the KERNAL (irq.s), so the music keeps playing. */
    POKE(0x01, 0x35);
    inflatemem((char *)BITMAP, (const char *)map_bmp_z);
    POKE(0x01, 0x36);
    inflatemem((char *)SCREEN, (const char *)map_scr_z);

    for (i = 0; i < 63; ++i) {              /* two sprites, 64 bytes apart */
        ((unsigned char *)SPRITES)[i] = cursor_data[i];
        ((unsigned char *)SPRITES + 64)[i] = cursor_data[i + 63];
    }
    POKE(SCREEN + 0x3F8, SPRITE_PTR);       /* sprite 0: white fill */
    POKE(SCREEN + 0x3F9, SPRITE_PTR + 1);   /* sprite 1: black outline */
    POKE(0xD027, 1);
    POKE(0xD028, 0);
    POKE(0xD017, 0);                        /* no sprite stretching */
    POKE(0xD01D, 0);
    POKE(0xD01B, 0);                        /* sprites in front */
    POKE(0xD01C, 0);                        /* hires sprites */

    for (i = 0; i < 5; ++i) {
        POKE(HUD_ROW_SCR + MONEY_COL + i, 0x70);    /* yellow on black */
    }
    for (i = 0; i < START_LIVES; ++i) {
        POKE(HUD_ROW_SCR + LIVES_COL + i, 0x20);    /* red on black */
    }
}

#pragma code-name (pop)
