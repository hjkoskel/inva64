#!/usr/bin/env python3
"""DOS 320x200 kartta -> C64 hires bitmap (320x200, 2 väriä / 8x8 solu)."""
import sys, zlib, itertools; sys.path.insert(0, 'src')
from c64map import PAL, F, F10, dist, nearest, BLACK,WHITE,RED,CYAN,PURPLE,GREEN,BLUE,YELLOW,ORANGE,BROWN,LRED,DGREY,GREY,LGREEN,LBLUE,LGREY
from PIL import Image
W,H = 320,200
TUFT = int(sys.argv[1]) if len(sys.argv)>1 else 1

def mc(rgb, x, y):
    r,g,b = rgb
    keep = (6<=x<=52 and 2<=y<=34)                 # vasen ylätalo: alkuperäiset sävyt
    if r<10 and b==0 and g>=150: return GREEN
    if 150<=r<=240 and 95<=g<=150 and 55<=b<=95: return LRED if keep else ORANGE
    if g>150 and g>r+30 and g>b+30: return LGREEN
    if r>200 and g>190 and b>220: return WHITE
    return nearest(rgb)

# Kyltit hires-koordinaateissa. cx = keskikohta, cy = solurivi (8 px) jolta kyltti alkaa
# rows = korkeus soluriveinä. Kyltin reunat osuvat aina 8x8-solujen rajoille.
SIGNS = [
 dict(t=["KIRJASTO"],        cx=118, cy=0,  rows=2, old=(96,2,140,16)),
 dict(t=["RAUTAA"],          cx=186, cy=0,  rows=2, old=(162,5,210,20), oy=4),
 dict(t=["MIÄL","SAIRAALA"], cx=283, cy=0,  rows=4, old=(250,8,316,32)),
 dict(t=["KUKKIA"],          cx=36,  cy=6,  rows=2, old=(12,44,60,68)),
 dict(t=["SIWA"],            cx=96,  cy=9,  rows=3, fg=BLUE, old=(76,66,116,96)),
 dict(t=["SORSAPUISTO"],     cx=182, cy=8,  rows=2, fg=RED, old=(134,60,196,83)),
 dict(t=["KIRPPU","TORI"],   cx=278, cy=11, rows=4, old=(252,88,304,120)),
 dict(t=["WC"],              cx=20,  cy=13, rows=2, old=(6,106,34,122)),
 dict(t=["UIMA","HALLI"],    cx=104, cy=14, rows=3, bg=LBLUE, border=None, old=(82,110,124,134)),
 dict(t=["ANKKA","LINNA"],   cx=28,  cy=18, rows=4, old=(6,134,44,184)),
 dict(t=["POLIS"],           cx=146, cy=20, rows=2, fg=BLUE, old=(128,160,164,175)),
 dict(t=["R"],               cx=216, cy=18, rows=2, fg=BLUE, old=(208,146,226,160)),
 dict(t=["DRUGS"],           cx=276, cy=17, rows=2, old=(252,141,300,161)),
 dict(t=["EMÄLÄT"],          cx=204, cy=22, rows=2, fg=WHITE, bg=BLACK, border=None, old=(182,176,224,190)),
 dict(t=["MONEY"],           cx=24,  cy=24, rows=1, fg=YELLOW, bg=BLACK, border=None, ys=1, fill=(0,192,319,199,BLACK)),
]

def glyph(ch, ys):
    if ch in F10: return F10[ch] if ys==2 else [F10[ch][i] for i in (2,4,6,8,9)]
    return [r for r in F[ch] for _ in range(ys)]
def tw(s, sx): return sum((len((F.get(c) or F10[c])[0])+1)*sx for c in s) - sx

def inpaint(px, mask):
    todo=set(mask)
    while todo:
        nxt=set()
        for (x,y) in todo:
            c={}
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
                q=(x+dx,y+dy)
                if 0<=q[0]<W and 0<=q[1]<H and q not in todo:
                    v=px[q[1]][q[0]]; c[v]=c.get(v,0)+1
            if c: px[y][x]=max(c,key=c.get)
            else: nxt.add((x,y))
        if nxt==todo: break
        todo=nxt

def draw_signs(px, prot):
    rects=[]
    for s in SIGNS:
        if 'old' in s:
            x0,y0,x1,y1=s['old']
            inpaint(px,[(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1)])
    for s in SIGNS:
        if 'fill' in s:
            x0,y0,x1,y1,c=s['fill']
            for y in range(y0,y1+1):
                for x in range(x0,x1+1): px[y][x]=c; prot.add((x,y))
        sx=2; ys=s.get('ys',2); lh=5*ys
        fg=s.get('fg',BLACK); bg=s.get('bg',WHITE)
        border=s.get('border',fg if fg!=WHITE else BLACK)
        tws=max(tw(l,sx) for l in s['t'])
        b = 1 if border is not None else 0
        wcells=-(-(tws+2*b+4)//8)                  # vähintään 2 px tyhjää sivuilla
        w=wcells*8; x0=((s['cx']-w//2)+4)//8*8
        x0=max(0,min(W-w,x0))
        y0=s['cy']*8 + s.get('oy',0)//8*8; h=s['rows']*8
        for y in range(y0,y0+h):
            for x in range(x0,x0+w):
                edge=b and (x in (x0,x0+w-1) or y in (y0,y0+h-1))
                px[y][x]=border if edge else bg; prot.add((x,y))
        n=len(s['t']); th=n*lh
        gap=(h-2*b-th)//(n+1)
        ty=y0+b+gap+((h-2*b-th)-(n+1)*gap)//2
        for l in s['t']:
            tx=x0+(w-tw(l,sx))//2
            for ch in l:
                g=glyph(ch,ys)
                for r,row in enumerate(g):
                    for c,v in enumerate(row):
                        if v=='#':
                            for k in range(sx): px[ty+r][tx+c*sx+k]=fg
                tx+=(len(g[0])+1)*sx
            ty+=lh+gap
        rects.append((" ".join(s['t']),x0,y0,w,h))
    return rects

def fix_cells(px, prot):
    scr=bytearray(1000)
    for cy in range(25):
        for cx in range(40):
            pts=[(cx*8+i,cy*8+j) for j in range(8) for i in range(8)]
            cnt={}
            for (x,y) in pts:
                v=px[y][x]; cnt[v]=cnt.get(v,0)+(1000 if (x,y) in prot else 1)
            cols=list(cnt)
            if len(cols)>2:
                best=min(itertools.combinations(cols,2),
                    key=lambda cb:sum(n*min(dist(PAL[c],PAL[a]) for a in cb) for c,n in cnt.items()))
                rm={c:min(best,key=lambda a:dist(PAL[c],PAL[a])) for c in cnt}
                for (x,y) in pts: px[y][x]=rm[px[y][x]]
                cols=list(best)
            cols.sort(key=lambda c:-cnt[c])
            bgc=cols[0]; fgc=cols[1] if len(cols)>1 else cols[0]
            scr[cy*40+cx]=(fgc<<4)|bgc                # bitti 1 = ylänibble, bitti 0 = alanibble
    return scr

def main():
    im=Image.open('orig.png').convert('RGB')
    px=[[mc(im.getpixel((x,y)),x,y) for x in range(W)] for y in range(H)]
    T=(GREEN,ORANGE,LGREY)
    new=[r[:] for r in px]                          # maaston reunojen siloitus
    for y in range(1,191):
        for x in range(1,W-1):
            if px[y][x] in T:
                n=[px[y+dy][x+dx] for dy in (-1,0,1) for dx in (-1,0,1)]
                if all(v in T for v in n): new[y][x]=max(T,key=n.count)
    px=new
    prot=set(); rects=draw_signs(px,prot)
    if TUFT:
        for cy in range(24):
            for cx in range(40):
                if (cx+cy)%2==0 and all(px[cy*8+j][cx*8+i]==GREEN for j in range(8) for i in range(8)):
                    for (i,j) in ((2,4),(3,3),(4,4)): px[cy*8+j][cx*8+i]=LGREEN
    scr=fix_cells(px,prot)
    bmp=bytearray(8000)
    for cy in range(25):
        for cx in range(40):
            v=scr[cy*40+cx]; fgc=v>>4
            for j in range(8):
                b=0
                for i in range(8): b=(b<<1)|(1 if px[cy*8+j][cx*8+i]==fgc and fgc!=(v&15) else 0)
                bmp[(cy*40+cx)*8+j]=b
    return px,bmp,scr,rects

if __name__=='__main__':
    px,bmp,scr,rects=main()
    open('out3/kartta_hires.art','wb').write(bytes([0,0x20])+bmp+scr+bytes([0]))   # Art Studio, $2000
    def deflate(b):
        c=zlib.compressobj(9,zlib.DEFLATED,-15); best=c.compress(b)+c.flush()
        try:
            import zopfli.zlib as zz; z=zz.compress(b,numiterations=200)[2:-4]
            if len(z)<len(best): best=z
        except ImportError: pass
        assert zlib.decompress(best,-15)==b; return best
    zb,zs=deflate(bytes(bmp)),deflate(bytes(scr))
    print('bitmap',len(zb),'screen',len(zs),'yht',len(zb)+len(zs))
    def arr(n,d):
        o="const unsigned char %s[%d] = {\n"%(n,len(d))
        for i in range(0,len(d),16): o+="  "+",".join("0x%02x"%v for v in d[i:i+16])+",\n"
        return o+"};\n"
    open('out3/kartta.c','w').write('/* C64 hires-kartta, raw deflate. Generoitu: hires.py */\n#include "kartta.h"\n\n/* bittikartta, purettuna 8000 tavua */\n'+arr("kartta_bmp_z",zb)+'\n/* screen RAM (värit), purettuna 1000 tavua */\n'+arr("kartta_scr_z",zs))
    open('out3/kartta.h','w').write("#ifndef KARTTA_H\n#define KARTTA_H\nextern const unsigned char kartta_bmp_z[%d];\nextern const unsigned char kartta_scr_z[%d];\nvoid kartta_nayta(void);\n#endif\n"%(len(zb),len(zs)))
    o=Image.new('RGB',(W,H))
    for y in range(H):
        for x in range(W): o.putpixel((x,y),PAL[px[y][x]])
    o.save('out3/kartta_hires_320x200.png'); o.resize((1280,800),Image.NEAREST).save('out3/kartta_hires_preview4x.png')
    import json; json.dump(rects,open('/tmp/rects.json','w'))
    for r in rects: print(r)
