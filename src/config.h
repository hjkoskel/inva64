/* Tunable game constants. Times are in frames (50 per second on PAL). */
#ifndef CONFIG_H
#define CONFIG_H

#define MONEY_REWARD      15    /* gained for the right place */
#define TIMEOUT_PENALTY   15    /* lost when the answer takes too long */
#define START_LIVES       3     /* the game ends when lives go below 0 */
#define ANSWER_FRAMES     250   /* time to answer, about 5 s (max 255) */

#define INTRO_WAIT_FRAMES 25    /* after the start key, before sample 1 */
#define READY_BLINK_MASK  0x20  /* READY text: on and off every 32 frames */
#define READY_X           120   /* READY text position on the title, */
#define READY_Y           176   /* in picture pixels (text is 80 x 16) */
#define INTRO_GAP_FRAMES  50    /* between sample 1 and sample 3 */
#define MAP_PAUSE_FRAMES  50    /* after sample 3, before the map */
#define ROUND_GAP_FRAMES  50    /* 1 s before the next place is picked */

/* Sound effects (SID voice 1, the music waits meanwhile). */
#define SFX_VOLUME        12    /* 0-15 */
#define BLONK_PITCH_START 0x16  /* life lost: pitch slides down from here */
#define BLONK_PITCH_END   0x05  /* ... to here, one step per frame */
#define BEEP_COUNT        3     /* money lost: this many beeps */
#define BEEP_PITCH        0x48  /* about 1 kHz */
#define BEEP_ON_FRAMES    4
#define BEEP_OFF_FRAMES   4

/* Cursor speed in pixels per frame, by how long a direction is held. */
#define CURSOR_SLOW       1
#define CURSOR_MID        2
#define CURSOR_FAST       4
#define CURSOR_MID_AFTER  5     /* frames held before CURSOR_MID */
#define CURSOR_FAST_AFTER 14    /* frames held before CURSOR_FAST */

#endif
