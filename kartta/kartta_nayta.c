/* Hires-kartan purku ja näyttö, cc65 / C64.
 *
 * Muistikartta (VIC-pankki 3):
 *   $C000-$C3E7  screen RAM: ylänibble = 1-bittien väri, alanibble = 0-bittien väri
 *   $E000-$FF3F  bittikartta KERNAL-ROMin alla olevassa RAMissa
 * Color RAMia ($D800) ei käytetä hires-tilassa.
 *
 *   cl65 -t c64 -O -Wl -D,__HIMEM__=0xC000 -o kartta.prg main.c kartta_nayta.c kartta.c
 */
#include <zlib.h>
#include <6502.h>
#include "kartta.h"

#define POKE(a,v) (*(unsigned char*)(a) = (v))
#define PEEK(a)   (*(unsigned char*)(a))

void kartta_nayta(void)
{
    unsigned char vanha01;

    POKE(0xD011, PEEK(0xD011) & 0xEF);          /* ruutu pimeäksi purun ajaksi */

    /* KERNAL pois näkyvistä purun ajaksi, koska inflate lukee purkamaansa
       dataa takaisin ($E000-alueelta luettaisiin muuten ROMia). */
    SEI();
    vanha01 = PEEK(0x01);
    POKE(0x01, (vanha01 & 0xF8) | 0x05);
    inflatemem((unsigned char*)0xE000, kartta_bmp_z);
    POKE(0x01, vanha01);
    CLI();

    inflatemem((unsigned char*)0xC000, kartta_scr_z);

    POKE(0xD020, 0);                             /* reunus musta */
    POKE(0xDD02, PEEK(0xDD02) | 0x03);
    POKE(0xDD00, PEEK(0xDD00) & 0xFC);           /* VIC-pankki 3: $C000-$FFFF */
    POKE(0xD018, 0x08);                          /* screen $C000, bittikartta $E000 */
    POKE(0xD016, 0x08);                          /* hires (multicolor pois) */
    POKE(0xD011, 0x3B);                          /* bittikarttatila, ruutu päälle */
}

/* Palauttaa hotspotin indeksin tai -1. x 0..319, y 0..199 */
signed char kartta_osuma(unsigned int x, unsigned char y)
{
    unsigned char i;
    const hotspot_t *h = hotspotit;
    for (i = 0; i < HOTSPOT_LKM; ++i, ++h) {
        if (x >= h->x0 && x < h->x0 + h->w && y >= h->y0 && y < h->y0 + h->h)
            return i;
    }
    return -1;
}
