"""Bake a seamless woven cloud-and-feather repeat for the duelist's jacket."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

size = 1024
mask = Image.new("L", (size, size))
pen = ImageDraw.Draw(mask)


def thread(origin, curves, width, light):
    x, y = origin
    points = [(x, y)]
    for x1, y1, x2, y2, x3, y3 in curves:
        for t in np.linspace(0, 1, 28)[1:]:
            u = 1 - t
            points.append((u**3*x + 3*u*u*t*x1 + 3*u*t*t*x2 + t**3*x3,
                           u**3*y + 3*u*u*t*y1 + 3*u*t*t*y2 + t**3*y3))
        x, y = x3, y3
    for row in range(-1, 5):
        for col in range(-2, 5):
            ox, oy = col * 256 + (row % 2)*128, row * 256
            pen.line([(ox+a, oy+b) for a,b in points], fill=light, width=width)


# A cloud head with a curling foot sits above each feather.
thread((20,153), [(44,151,61,119,81,126),(92,123,100,129,100,137),
       (112,127,133,122,144,130),(156,140,139,153,129,147),
       (124,142,129,138,134,140)], 4, 165)
thread((24,159), [(50,155,67,130,80,133),(91,131,95,137,94,143),
       (113,140,112,162,92,168),(75,176,58,168,49,177)], 3, 118)
thread((63,241), [(87,217,133,214,163,169),(184,137,189,84,220,52)], 4, 198)
for j in range(10):
    t = j/10
    x, y = 132+70*t, 200-125*t
    thread((x,y),[(x-10,y-8,x-24+16*t,y-24,x-13+12*t,y-46+18*t)], 2, 135)
    thread((x+3,y+1),[(x+28-11*t,y-3,x+29-15*t,y-13,x+32-15*t,y-27)], 3, 154)

y,x = np.indices((size,size))
motif = np.asarray(mask).astype(float)/255
warp = np.sin(2*np.pi*x/4) * np.cos(2*np.pi*y/16)
weft = np.cos(2*np.pi*y/4) * np.sin(2*np.pi*(x+y)/32)
slub = (np.sin(2*np.pi*(2*x+y)/size) + np.cos(2*np.pi*(3*y-x)/size))*.5
ground = np.array([60.,88.,83.]) + (3*warp+2*weft+3*slub)[...,None]
yarn = np.array([153.,146.,111.]) + (15*warp+6*weft)[...,None]
rgb = ground*(1-motif[...,None]) + yarn*motif[...,None]
out = Path(__file__).resolve().parents[1]/"public"/"textures"/"heron-damask.jpg"
Image.fromarray(rgb.clip(0,255).astype("uint8")).save(out, quality=94, subsampling=0)
