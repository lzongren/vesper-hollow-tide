"""Bake the pilgrim's embroidered rain mantle. Requires NumPy and Pillow."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageOps

SIZE = 1024
OUT = Path(__file__).resolve().parents[1] / 'public/textures'
mask = Image.new('L', (SIZE, SIZE))
pen = ImageDraw.Draw(mask)


def stroke(points, width, shade=255):
    pen.line(points, fill=shade, width=width, joint='curve')


def curve(start, segments, width, shade=255):
    path = []
    t = np.linspace(0, 1, 40)[:,None]
    for c1, c2, end in segments:
        p = (1-t)**3*np.array(start) + 3*t*(1-t)**2*np.array(c1) + 3*t*t*(1-t)*np.array(c2) + t**3*np.array(end)
        path.extend(map(tuple,p)); start=end
    stroke(path,width,shade)


# Half of a paired heron crest. Contours, coverts and separate primaries share a stitch direction.
curve((490,420), [((473,411),(457,408),(451,415)),((426,430),(458,457),(451,478)),((431,504),(402,495),(372,474)),((309,434),(283,383),(254,335)),((272,419),(304,469),(344,505)),((388,544),(428,561),(458,540)),((498,512),(501,475),(476,453)),((459,432),(477,426),(490,420))],6)
curve((490,420), [((497,421),(506,428),(509,432)),((500,430),(486,428),(479,426))],3)
for i in range(12):
    u=i/11; sx,sy=420-54*u,501-39*u; tx,ty=266+95*u,363+162*u
    curve((sx,sy), [((sx-49,sy-31),(tx+33,ty+54),(tx,ty)),((tx+13,ty+58),(sx-40,sy+6),(sx-6,sy+17))],3 if i%3 else 5,213)
for i in range(5):
    curve((435+4*i,542), [((409,568+i*5),(383,572+i*8),(369-i*10,575+i*8)),((394,556+i*4),(418,548),(435+4*i,542))],3,203)
pen.ellipse((455,416,462,423),fill=225)
mask=Image.fromarray(np.maximum(np.asarray(mask),np.asarray(ImageOps.mirror(mask))))
pen=ImageDraw.Draw(mask)
for side in [-1,1]:
    for offset in [23,29,64,70]:
        x=offset if side==-1 else SIZE-offset
        stroke([(x,0),(x,SIZE)],3)
    x=43 if side==-1 else SIZE-43
    for y in range(-32,SIZE,42):
        stroke([(x-10,y),(x+10,y+11),(x-10,y+23),(x+10,y+35)],3,210)
for y in (751,760,834,843,940,950): stroke([(24,y),(1000,y)],3)
for x in range(22,SIZE-30,64):
    curve((x,801), [((x+15,759),(x+37,762),(x+30,789)),((x+20,808),(x+14,783),(x+28,780)),((x+50,756),(x+42,825),(x+64,801))],5,220)
for x in range(48,1000,55):
    curve((x,918), [((x-17,892),(x-7,884),(x,868)),((x+10,885),(x+17,894),(x,918))],4,217)
for y in range(85,738,62):
    for x in range(96+(y//62%2)*24,955,55):
        if 240<x<785 and 320<y<635:continue
        stroke([(x-7,y),(x,y-8),(x+7,y),(x,y+8),(x-7,y)],2,92)
y,x=np.mgrid[:SIZE,:SIZE]; rng=np.random.default_rng(6203)
thread=np.asarray(mask).astype(float)/255
rib=.6*np.sin(x*2.0)+.55*np.cos(y*2.1)+.32*np.sin((x+y)*1.8)
coarse=np.asarray(Image.fromarray(rng.integers(0,255,(28,23),dtype=np.uint8)).resize((SIZE,SIZE),Image.Resampling.BICUBIC))/255
base=np.array([85,30,33])+coarse[...,None]*[36,16,14]
gold=np.array([156,104,46])+(coarse+.28*np.sin((x-y)*1.7))[...,None]*[62,53,36]
color=base*(1-thread[...,None])+gold*thread[...,None]+(rib*3+rng.normal(0,2,x.shape))[...,None]
height=.44*thread+.064*rib
ny,nx=np.gradient(height);normal=np.stack((-nx,ny,np.ones_like(nx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
for suffix,data in [('color',color),('normal',(1+normal)*127.5)]:
    Image.fromarray(np.uint8(np.clip(data,0,255))).save(OUT/f'pilgrim-brocade-{suffix}.jpg',quality=91,subsampling=0)
