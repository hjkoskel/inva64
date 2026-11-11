/* Shared declarations of the Invataxi game. */
#ifndef GAME_H
#define GAME_H

#include "config.h"
#include "samples.h"            /* generated: CLIP_nn */

#define POKE(a, v) (*(unsigned char *)(a) = (v))
#define PEEK(a)    (*(unsigned char *)(a))

/* Places in the order of the click-area table in playfield.c. */
#define NUM_PLACES       13     /* places that can be asked for */
#define PLACE_KIRPPUTORI 13     /* on the map, never asked for */
#define NUM_AREAS        14

/* Input bits, as on a joystick port but active high. */
#define IN_UP    0x01
#define IN_DOWN  0x02
#define IN_LEFT  0x04
#define IN_RIGHT 0x08
#define IN_FIRE  0x10
#define IN_MOVE  0x0F

/* irq.s */
extern volatile unsigned char frame;
extern unsigned char music_paused;
void irq_init(void);
void wait_frame(void);

/* play.s */
void digi_begin(void);
void __fastcall__ digi_play(unsigned char clip);
void digi_end(void);

/* data.s */
extern const unsigned char map_bmp_z[];
extern const unsigned char map_scr_z[];
extern const unsigned char cursor_data[126];

/* input.c */
unsigned char input_read(void);
unsigned char input_any(void);
void __fastcall__ cursor_move(unsigned char in);
extern unsigned int cursor_x;       /* 0..319 */
extern unsigned char cursor_y;      /* 0..199 */

/* playfield.c */
void playfield_show(void);
void playfield_on(void);
signed char playfield_hit(void);
void hud_money(void);
void hud_lives(void);
void money_digits(void);
extern unsigned char digits[5];     /* money as screen codes */

/* game.c */
extern unsigned int money;
extern signed char lives;
extern unsigned int seed;
void __fastcall__ say(unsigned char clip);
void __fastcall__ pause(unsigned char frames);
void game_run(void);

/* kuolit.c */
void kuolit(void);

#endif
