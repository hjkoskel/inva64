/* Game logic: rounds, money, lives. */
#include "game.h"

unsigned int money;
signed char lives;
unsigned int seed;

/* Sample of each place, in the order of the click-area table. */
static const unsigned char place_clip[NUM_PLACES] = {
    CLIP_10,    /* UIMAHALLI */
    CLIP_12,    /* DRUGS */
    CLIP_13,    /* MAKKARI */
    CLIP_14,    /* KUKKIA */
    CLIP_16,    /* RKIOSKI */
    CLIP_17,    /* SORSAPUISTO */
    CLIP_18,    /* WC */
    CLIP_19,    /* ANKKALINNA */
    CLIP_20,    /* KIRJASTO */
    CLIP_21,    /* SAIRAALA */
    CLIP_22,    /* POLIS */
    CLIP_23,    /* RAUTAA */
    CLIP_24     /* SIWA */
};

/* "nyt tue", "vie mut", "mä haluun" */
static const unsigned char prefix_clip[3] = { CLIP_02, CLIP_05, CLIP_06 };

unsigned char last_place = 0xFF;    /* the place asked for */
static unsigned char prev_in;

/* Play one clip. The music stops while it plays. */
void __fastcall__ say(unsigned char clip)
{
    digi_begin();
    digi_play(clip);
    digi_end();
}

/* Wait, keeping the cursor alive (it is off during the intro). */
void __fastcall__ pause(unsigned char frames)
{
    while (frames) {
        wait_frame();
        prev_in = input_read();
        cursor_move(prev_in);
        --frames;
    }
}

/* Sound effects use SID voice 1. The music does not touch the SID while
   music_paused is set; it goes on from the same position afterwards. */
static void sfx_begin(void)
{
    music_paused = 1;
    POKE(0xD404, 0);
    POKE(0xD40B, 0);
    POKE(0xD412, 0);
    POKE(0xD400, 0);
    POKE(0xD418, SFX_VOLUME);
}

static void sfx_end(void)
{
    POKE(0xD404, 0);
    POKE(0xD406, 0);
    music_paused = 0;
}

/* "Blonk": a pulse tone that slides down. Played when a life is lost. */
static void sfx_blonk(void)
{
    unsigned char pitch;

    sfx_begin();
    POKE(0xD402, 0x00);                 /* pulse width 50% */
    POKE(0xD403, 0x08);
    POKE(0xD405, 0x0A);                 /* fast attack, slow decay */
    POKE(0xD406, 0x00);
    for (pitch = BLONK_PITCH_START; pitch != BLONK_PITCH_END; --pitch) {
        POKE(0xD401, pitch);
        POKE(0xD404, 0x41);             /* pulse, gate on */
        pause(1);
    }
    sfx_end();
}

/* A few short beeps. Played when money is lost. */
static void sfx_beeps(void)
{
    unsigned char i;

    sfx_begin();
    POKE(0xD405, 0x00);
    POKE(0xD406, 0xF0);                 /* full level while the gate is on */
    POKE(0xD401, BEEP_PITCH);
    for (i = 0; i < BEEP_COUNT; ++i) {
        POKE(0xD404, 0x11);             /* triangle, gate on */
        pause(BEEP_ON_FRAMES);
        POKE(0xD404, 0x10);             /* gate off */
        pause(BEEP_OFF_FRAMES);
    }
    sfx_end();
}

/* 16-bit xorshift; returns a number below n. mask = 2^k - 1 >= n - 1. */
static unsigned char rnd(unsigned char n, unsigned char mask)
{
    unsigned char r;
    do {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        seed ^= seed << 8;
        r = (unsigned char)seed & mask;
    } while (r >= n);
    return r;
}

/* One round. */
static void play_round(void)
{
    unsigned char place, t, in;
    signed char hit;

    do {
        place = rnd(NUM_PLACES, 15);
    } while (place == last_place);
    last_place = place;

    digi_begin();
    digi_play(prefix_clip[rnd(3, 3)]);
    digi_play(place_clip[place]);
    digi_end();

    for (t = ANSWER_FRAMES; t; --t) {
        wait_frame();
        in = input_read();
        cursor_move(in);
        if ((in & IN_FIRE) && !(prev_in & IN_FIRE)) {
            seed += frame;              /* stir with the player's timing */
            if (!seed) {
                seed = 1;
            }
            hit = playfield_hit();
            if (hit == (signed char)place) {
                money += MONEY_REWARD;
                hud_money();
                say(CLIP_08);           /* "kiitti" */
                prev_in = in;
                return;
            }
            if (hit >= 0) {             /* wrong place; empty ground is ignored */
                say(CLIP_11);
                --lives;
                hud_lives();
                sfx_blonk();
                prev_in = in;
                return;
            }
        }
        prev_in = in;
    }

    say(CLIP_07);                       /* "liian kauan" */
    if (money) {
        money = money > TIMEOUT_PENALTY ? money - TIMEOUT_PENALTY : 0;
        hud_money();
        sfx_beeps();
    }
}

void game_run(void)
{
    if (!seed) {
        seed = 1;
    }
    for (;;) {
        money = 0;
        lives = START_LIVES;
        playfield_on();
        while (lives >= 0) {
            pause(ROUND_GAP_FRAMES);
            play_round();
        }
        kuolit();
    }
}
