/*
 * Input and the cursor.
 *
 * Joystick in port 2, or the keyboard: W/A/S/D move, SPACE or RETURN is
 * fire. The keyboard matrix is read directly, so several keys work at once.
 */
#include "game.h"

unsigned int cursor_x = 160;
unsigned char cursor_y = 100;

static unsigned char held;      /* frames a direction has been held */

/* Returns IN_* bits. */
unsigned char input_read(void)
{
    unsigned char in, k;

    POKE(0xDC00, 0xFF);
    in = ~PEEK(0xDC00) & 0x1F;
    if (in) {
        /* A joystick in port 2 pulls matrix lines low, which would show
           up as key presses. Use the joystick alone. */
        return in;
    }
    POKE(0xDC00, 0xFD);
    k = ~PEEK(0xDC01);
    if (k & 0x02) in |= IN_UP;          /* W */
    if (k & 0x20) in |= IN_DOWN;        /* S */
    if (k & 0x04) in |= IN_LEFT;        /* A */
    POKE(0xDC00, 0xFB);
    if (!(PEEK(0xDC01) & 0x04)) in |= IN_RIGHT;     /* D */
    POKE(0xDC00, 0x7F);
    if (!(PEEK(0xDC01) & 0x10)) in |= IN_FIRE;      /* SPACE */
    POKE(0xDC00, 0xFE);
    if (!(PEEK(0xDC01) & 0x02)) in |= IN_FIRE;      /* RETURN */
    return in;
}

/* Non-zero when fire or any key is down. */
unsigned char input_any(void)
{
    POKE(0xDC00, 0xFF);
    if ((PEEK(0xDC00) & 0x10) == 0) {
        return 1;
    }
    POKE(0xDC00, 0x00);
    return PEEK(0xDC01) != 0xFF;
}

/* Move the cursor by the input bits and place the two sprites. */
void __fastcall__ cursor_move(unsigned char in)
{
    static unsigned char s;
    static unsigned int sx;

    if (in & IN_MOVE) {
        if (held != 255) {
            ++held;
        }
    } else {
        held = 0;
    }
    s = held < CURSOR_MID_AFTER ? CURSOR_SLOW
      : held < CURSOR_FAST_AFTER ? CURSOR_MID : CURSOR_FAST;

    if (in & IN_UP) {
        cursor_y = cursor_y > s ? cursor_y - s : 0;
    }
    if (in & IN_DOWN) {
        cursor_y += s;
        if (cursor_y > 199) {
            cursor_y = 199;
        }
    }
    if (in & IN_LEFT) {
        cursor_x = cursor_x > s ? cursor_x - s : 0;
    }
    if (in & IN_RIGHT) {
        cursor_x += s;
        if (cursor_x > 319) {
            cursor_x = 319;
        }
    }

    sx = cursor_x + 24;
    POKE(0xD000, (unsigned char)sx);
    POKE(0xD002, (unsigned char)sx);
    POKE(0xD010, sx > 255 ? 3 : 0);
    POKE(0xD001, cursor_y + 50);
    POKE(0xD003, cursor_y + 50);
}
