"""Bake the Saint's patchwork madder silk, lotus medallions and couched seams."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

width, height = 768, 1024
mask = Image.new("L", (width, height))
pen = ImageDraw.Draw(mask)
def line(points, value, thickness):
    pen.line([tuple(p) for p in points], fill=value, width=thickness)
def rosette(x, y, radius):
    for k in range(8):
        a = k*np.pi/4
        u = np.linspace(0,1,41)
        for sign in [-1,1]:
            reach = radius*(0.17+0.80*u)
            arc = sign*0.18*np.sin(np.pi*u)
            line(np.stack([x+reach*np.cos(a+arc),y+reach*np.sin(a+arc)],axis=1), 225, 3)
    pen.ellipse((x-4,y-4,x+4,y+4),fill=205)
for row in range(5):
    for col in range(4):
        x,y=98+col*192+(row%2)*40,94+row*212
        rosette(x,y,51 if (col+row)%2 else 65)
        for sign in [-1,1]:
            t=np.linspace(0,1,60)
            line(np.stack([x+sign*(15+65*t), y+52+12*np.sin(t*np.pi*2)-22*t],axis=1),157,2)
for x in [13,24,48,width-49,width-25,width-14]:
    pen.line((x,0,x,height),fill=194,width=4)
for y in range(-32,height,32):
    for origin in [27,width-45]:
        line([(origin,y),(origin+14,y+8),(origin+2,y+16),(origin+14,y+24),(origin,y+32)],217,3)

y,x=np.indices((height,width))
warp=np.sin(2*np.pi*x/3.2)*np.cos(2*np.pi*y/12)
weft=np.cos(2*np.pi*y/4)*np.sin(2*np.pi*(x+y)/16)
patch=((x//192 + (y//212)*3)%5)/4
base=np.array([131.,67.,60.]) + patch[...,None]*[21,21,18]
base+=(warp*4+weft*3)[...,None]
yarn=np.array([215.,170.,108.])+(warp*12+weft*7)[...,None]
motif=np.asarray(mask)/255
cloth=base*(1-motif[...,None])+yarn*motif[...,None]
seam=((x%192<4)|(y%212<4)) & (x>50)&(x<width-50)
cloth[seam]*=0.72
dest=Path(__file__).resolve().parents[1]/"public"/"textures"/"cinder-brocade.jpg"
Image.fromarray(cloth.clip(0,255).astype("uint8")).save(dest,quality=94,subsampling=0)
