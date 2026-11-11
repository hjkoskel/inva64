#ifndef KARTTA_H
#define KARTTA_H
extern const unsigned char kartta_bmp_z[2436];
extern const unsigned char kartta_scr_z[470];
void kartta_nayta(void);
signed char kartta_osuma(unsigned int x, unsigned char y);

/* Hotspotit (hires-pikselit): x0, y0, w, h */
typedef struct { unsigned int x0; unsigned char y0, w, h; } hotspot_t;
#define HOTSPOT_LKM 15
extern const hotspot_t hotspotit[HOTSPOT_LKM];
extern const char * const hotspot_nimet[HOTSPOT_LKM];
#endif
