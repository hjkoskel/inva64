#!/usr/bin/env python3
"""DOS 320x200 kartta -> C64 multicolor bitmap (160x200, Koala).
Kyltit piirretään uudelleen isolla 'fat pixel' -fontilla."""
import sys, itertools
from PIL import Image

PAL = [(0,0,0),(255,255,255),(0x81,0x33,0x38),(0x75,0xce,0xc8),(0x8e,0x3c,0x97),
       (0x56,0xac,0x4d),(0x2e,0x2c,0x9b),(0xed,0xf1,0x71),(0x8e,0x50,0x29),(0x55,0x38,0x00),
       (0xc4,0x6c,0x71),(0x4a,0x4a,0x4a),(0x7b,0x7b,0x7b),(0xa9,0xff,0x9f),(0x70,0x6d,0xeb),(0xb2,0xb2,0xb2)]
BLACK,WHITE,RED,CYAN,PURPLE,GREEN,BLUE,YELLOW,ORANGE,BROWN,LRED,DGREY,GREY,LGREEN,LBLUE,LGREY=range(16)
BG = GREEN

def dist(a,b):
    return 2*(a[0]-b[0])**2+4*(a[1]-b[1])**2+3*(a[2]-b[2])**2
def nearest(rgb):
    return min(range(16), key=lambda i: dist(rgb,PAL[i]))

def map_color(rgb):
    r,g,b = rgb
    if r<10 and b==0 and g>=150:              # nurmikon vihreät
        return LGREEN if g>=239 else GREEN
    if 150<=r<=240 and 95<=g<=150 and 55<=b<=95:   # hiekkapolku
        return LRED if r>=223 else ORANGE
    if g>150 and g>r+30 and g>b+30:            # vihreät rakennukset
        return LGREEN
    if r>200 and g>190 and b>220:              # vaalea liila julkisivu
        return WHITE
    return nearest(rgb)

# ---------- fontti: 5 riviä, jokainen rivi tuplataan pystyyn (=10 riviä) ----------
F = {
 'A':[".#.","#.#","###","#.#","#.#"], 'C':[".##","#..","#..","#..",".##"],
 'D':["##.","#.#","#.#","#.#","##."], 'E':["###","#..","##.","#..","###"],
 'G':[".##","#..","#.#","#.#",".##"], 'H':["#.#","#.#","###","#.#","#.#"],
 'I':["###",".#.",".#.",".#.","###"], 'J':["..#","..#","..#","#.#",".#."],
 'K':["#.#","#.#","##.","#.#","#.#"], 'L':["#..","#..","#..","#..","###"],
 'M':["#...#","##.##","#.#.#","#...#","#...#"], 'N':["#..#","##.#","#.##","#..#","#..#"],
 'O':["###","#.#","#.#","#.#","###"], 'P':["##.","#.#","##.","#..","#.."],
 'R':["##.","#.#","##.","#.#","#.#"], 'S':[".##","#..",".#.","..#","##."],
 'T':["###",".#.",".#.",".#.",".#."], 'U':["#.#","#.#","#.#","#.#","###"],
 'W':["#...#","#...#","#.#.#","##.##","#...#"], 'Y':["#.#","#.#",".#.",".#.",".#."],
 ' ':["..","..","..","..",".."],
}
# Ä ja Ö suoraan 10 rivin korkuisina (pisteet + 8 rivin kirjain)
F10 = {
 'Ä':["#.#","...",".#.",".#.","#.#","#.#","###","###","#.#","#.#"],
 'Ö':["#.#","...","###","###","#.#","#.#","#.#","#.#","###","###"],
}
def glyph(ch, ys):
    if ch in F10 and ys==2: return F10[ch]
    if ch in F10:  # pieni koko: pudota pisteet pois
        return [F10[ch][i] for i in (2,4,6,8,9)]
    return [r for r in F[ch] for _ in range(ys)]
def text_w(s): return sum(len((F.get(c) or F10[c])[0])+1 for c in s)-1

# ---------- kyltit (fat-pikselikoordinaatit: x 0..159, y 0..199) ----------
# old = vanha alue joka pyyhitään (täytetään ympäristöllä) ennen piirtoa
SIGNS = [
 dict(lines=["KIRJASTO"],     cx=59,  y=0,   old=(49,3,69,16)),
 dict(lines=["RAUTAA"],       cx=93,  y=5,   old=(82,6,104,20)),
 dict(lines=["MIÄL","SAIRAALA"], cx=141, y=1, old=(126,9,157,32), gap=1),
 dict(lines=["KUKKIA"],       cx=18,  y=46,  old=(6,44,30,68)),
 dict(lines=["SIWA"],         cx=48,  y=71,  fg=BLUE),
 dict(lines=["SORSAPUISTO"],  cx=91,  y=63,  fg=RED, old=(67,60,98,83)),
 dict(lines=["KIRPPU","TORI"],cx=139, y=93,  old=(126,88,152,120), gap=1, padx=3),
 dict(lines=["WC"],           cx=10,  y=108, old=(3,106,17,122)),
 dict(lines=["UIMA","HALLI"], cx=51,  y=112, bgc=LBLUE, border=None, padx=0, pady=0, gap=1),
 dict(lines=["ANKKA","LINNA"],cx=13,  y=146, old=(3,134,22,184), gap=1),
 dict(lines=["POLIS"],        cx=73,  y=162, fg=BLUE),
 dict(lines=["DRUGS"],        cx=138, y=143, old=(126,141,150,161)),
 dict(lines=["EMÄLÄT"],       cx=102, y=177, fg=WHITE, bgc=BLACK, border=None, old=(91,176,111,190)),
 dict(lines=["R"],            cx=106, y=147, fg=BLUE),
 dict(lines=["MONEY"],        cx=11,  y=193, fg=YELLOW, bgc=BLACK, border=None, ys=1, pady=0, padx=1, fill=(0,192,159,199,BLACK)),
]

def inpaint(px, mask):
    """täytä maskatut pikselit naapureiden yleisimmällä värillä"""
    W,H=160,200
    todo=set(mask)
    while todo:
        nxt=set()
        for (x,y) in list(todo):
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
    for s in SIGNS:
        if 'old' in s:
            x0,y0,x1,y1=s['old']
            inpaint(px,[(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1)])
        if 'fill' in s:
            x0,y0,x1,y1,c=s['fill']
            for y in range(y0,y1+1):
                for x in range(x0,x1+1): px[y][x]=c; prot.add((x,y))
    for s in SIGNS:
        ys=s.get('ys',2); gap=s.get('gap',1); padx=s.get('padx',1); pady=s.get('pady',1)
        fg=s.get('fg',BLACK); bgc=s.get('bgc',WHITE); border=s.get('border',BLACK)
        lines=s['lines']; lh=5*ys
        tw=max(text_w(l) for l in lines)
        th=len(lines)*lh+(len(lines)-1)*gap
        b=1 if border is not None else 0
        w=tw+2*padx+2*b; h=th+2*pady+2*b
        x0=s['cx']-w//2; y0=s['y']
        for y in range(y0,y0+h):
            for x in range(x0,x0+w):
                edge = b and (x in (x0,x0+w-1) or y in (y0,y0+h-1))
                px[y][x]=border if edge else bgc; prot.add((x,y))
        ty=y0+b+pady
        for l in lines:
            tx=x0+b+padx+(tw-text_w(l))//2
            for ch in l:
                g=glyph(ch,ys)
                for r,row in enumerate(g):
                    for c,v in enumerate(row):
                        if v=='#': px[ty+r][tx+c]=fg
                tx+=len(g[0])+1
            ty+=lh+gap

def fix_cells(px, prot):
    """max 3 väriä + tausta per 4x8 solu"""
    cells=[]
    for cy in range(25):
        for cx in range(40):
            pts=[(cx*4+i,cy*8+j) for j in range(8) for i in range(4)]
            cnt={}
            for (x,y) in pts:
                w=1000 if (x,y) in prot else 1
                cnt[px[y][x]]=cnt.get(px[y][x],0)+w
            cols=[c for c in cnt if c!=BG]
            if len(cols)>3:
                best=None
                for combo in itertools.combinations(cols,3):
                    allow=combo+(BG,)
                    err=sum(n*min(dist(PAL[c],PAL[a]) for a in allow) for c,n in cnt.items())
                    if best is None or err<best[0]: best=(err,combo)
                allow=best[1]+(BG,)
                remap={c:min(allow,key=lambda a:dist(PAL[c],PAL[a])) for c in cnt}
                for (x,y) in pts: px[y][x]=remap[px[y][x]]
                cols=list(best[1])
            cells.append(sorted(cols, key=lambda c:-cnt[c])+[0]*(3-len(cols)))
    return cells

def write_koala(px, cells, fn):
    bmp=bytearray(8000); scr=bytearray(1000); col=bytearray(1000)
    for n,(c1,c2,c3) in enumerate(cells):
        cy,cx=divmod(n,40)
        scr[n]=(c1<<4)|c2; col[n]=c3
        code={BG:0}; code.setdefault(c1,1); code.setdefault(c2,2); code.setdefault(c3,3)
        for j in range(8):
            b=0
            for i in range(4):
                b=(b<<2)|code[px[cy*8+j][cx*4+i]]
            bmp[n*8+j]=b
    with open(fn,'wb') as f:
        f.write(bytes([0x00,0x60])+bmp+scr+col+bytes([BG]))

def pick(a,b):
    """kahdesta hires-pikselistä yksi leveä: ääriviiva > kohde > nurmikko"""
    if a==b: return a
    if BLACK in (a,b): return BLACK
    grass=(GREEN,LGREEN)
    if a in grass and b not in grass: return b
    return a

def main(src, out):
    im=Image.open(src).convert('RGB')
    px=[[0]*160 for _ in range(200)]
    for y in range(200):
        for x in range(160):
            a=im.getpixel((2*x,y)); b=im.getpixel((2*x+1,y))
            ia,ib=map_color(a),map_color(b)
            px[y][x]=pick(ia,ib)
    prot=set()
    draw_signs(px,prot)
    cells=fix_cells(px,prot)
    write_koala(px,cells,out+'.kla')
    o=Image.new('RGB',(320,200))
    for y in range(200):
        for x in range(160):
            o.putpixel((2*x,y),PAL[px[y][x]]); o.putpixel((2*x+1,y),PAL[px[y][x]])
    o.save(out+'_320x200.png')
    o.resize((1280,800),Image.NEAREST).save(out+'_preview4x.png')

if __name__=='__main__':
    main(sys.argv[1], sys.argv[2])
