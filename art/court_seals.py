"""Bake the three original court medallions. Run with NumPy and Pillow."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from cast_bell import grain

ROOT = Path(__file__).resolve().parents[1]
TEXTURES = ROOT / 'public' / 'textures'
SIZE = 1536
TAU = 2 * np.pi

# Each sector is drawn in tangential/radial coordinates. Its curves remain
# continuous around the centre as the motif is rotated into the next sector.
def motif(name):
    mask = Image.new('L', (SIZE, SIZE))
    draw = ImageDraw.Draw(mask)

    def curve(angle, start, *segments, width=.007):
        t = np.linspace(0, 1, 40)[:, None]
        path = []
        for a, b, end in segments:
            points = ((1-t)**3 * np.array(start) + 3*t*(1-t)**2 * np.array(a)
                      + 3*t*t*(1-t)*np.array(b) + t**3 * np.array(end))
            for x, y in points:
                px = x*np.cos(angle) - y*np.sin(angle)
                py = x*np.sin(angle) + y*np.cos(angle)
                path.append((round((1+px)*SIZE/2), round((1+py)*SIZE/2)))
            start = end
        draw.line(path, fill=255, width=max(1, round(width*SIZE/2)))

    for r, width in ((.10,.008),(.126,.013),(.712,.008),(.732,.012),(.904,.008),(.920,.014),(.978,.01)):
        lo, hi = (1-r)*SIZE/2, (1+r)*SIZE/2
        draw.ellipse((lo,lo,hi,hi), outline=255, width=round(width*SIZE/2))

    for i in range(32):
        angle = TAU*i/32
        curve(angle, (-.085,.815), ((-.061,.884),(-.015,.888),(0,.837)),
              ((.018,.776),(.067,.772),(.086,.815)))
        curve(angle, (-.016,.948), ((-.014,.957),(.014,.957),(.016,.948)),
              ((.011,.936),(-.011,.936),(-.016,.948)))

    count = {'lotus': 10, 'plume': 9, 'cinder': 8}[name]
    for i in range(count):
        angle = TAU*i/count
        if name == 'lotus':
            for sign in (-1,1):
                curve(angle,(0,.136),((sign*.071,.265),(sign*.171,.406),(sign*.126,.508)),
                      ((sign*.100,.575),(sign*.032,.62),(0,.690)),width=.012)
                curve(angle,(0,.235),((sign*.042,.34),(sign*.083,.44),(sign*.076,.485)),
                      ((sign*.071,.511),(sign*.022,.543),(0,.57)),width=.006)
            curve(angle,(0,.157),((-.006,.31),(.015,.47),(0,.528)))
        elif name == 'plume':
            curve(angle,(-.042,.135),((-.082,.32),(.125,.489),(.146,.685)),width=.013)
            curve(angle,(-.038,.193),((-.181,.35),(-.082,.563),(.146,.685)),
                  ((.201,.526),(.099,.281),(-.038,.193)),width=.010)
            for j in range(6):
                t = j/6
                y, x = .28+.28*t, -.022+.119*t
                curve(angle,(x,y),((x-.035,y+.022),(x-.080,y+.046),(x-.10*(1-.35*t),y+.091)))
                curve(angle,(x,y),((x+.033,y+.033),(x+.068,y+.041),(x+.08*(1-.55*t),y+.085)))
        else:
            curve(angle,(-.04,.14),((-.185,.285),(-.08,.403),(-.058,.447)),
                  ((-.038,.528),(-.134,.541),(.018,.685)),
                  ((-.003,.562),(.176,.489),(.128,.374)),
                  ((.109,.414),(.060,.433),(.071,.352)),
                  ((.095,.28),(.067,.205),(-.04,.14)), width=.013)
            curve(angle,(0,.24),((-.088,.339),(.067,.399),(.008,.514)),
                  ((.131,.411),(.052,.336),(0,.24)),width=.008)
    return np.asarray(mask, dtype=np.float32)/255


def encode(name, seed, stone_tint):
    rng = np.random.default_rng(seed)
    axis = (np.arange(SIZE, dtype=np.float32)+.5)*2/SIZE-1
    x, y = axis[None,:], axis[:,None]
    radius = np.hypot(x,y)
    angle = np.arctan2(y,x)
    coarse = grain(SIZE, 12, 12, rng).astype('float32')
    chips = grain(SIZE, 280, 280, rng).astype('float32')
    detail = rng.normal(0, 1, (SIZE,SIZE)).astype('float32')
    jitter = .0008*chips + .0016*coarse
    r = radius+jitter
    # Deep joints divide the engraved disc into replaceable fitted stones.
    edge = np.minimum.reduce([abs(r-i) for i in (.13,.40,.72,.916,.992)])
    for lo,hi,sectors,offset in ((.13,.40,5,.37),(.40,.72,10,.68),(.72,.916,16,.1),(.916,1,24,.6)):
        radial_edge = abs(np.sin((angle+offset)*sectors/2))*2*radius/sectors
        edge = np.minimum(edge, np.where((r>lo)&(r<hi), radial_edge+jitter, 2))
    joint = np.clip(1-edge/.0055,0,1)
    inlay = motif(name)*np.clip(.96+.20*chips+.09*coarse,0,1)*(1-joint)
    natural = np.asarray(Image.open(TEXTURES/'rock-color.jpg').convert('L').resize((SIZE,SIZE)),dtype=np.float32)
    natural = (natural-natural.mean()) / max(natural.std(),1)
    fleck = .28*natural+.33*chips+.12*detail+.26*coarse
    stone = np.array(stone_tint) + 16*fleck[...,None]
    oxide = np.clip(.32+.29*coarse+.26*chips,0,1)[...,None]
    bronze = (1-oxide)*np.array([173,133,76]) + oxide*np.array([64,90,77])
    color = (stone*(1-inlay[...,None])+bronze*inlay[...,None])*(1-.52*joint[...,None])
    wet = np.clip(.48-.37*coarse+.20*natural,0,1)
    rough = np.clip(.72-.39*wet+.045*chips-.10*inlay+.21*joint,.22,.94)
    packed = np.stack((1-.48*joint,rough,.03+.80*inlay),axis=-1)
    relief = -.95*joint + .14*inlay + .37*natural+.11*chips+.025*detail
    dy, dx = np.gradient(relief)
    normal = np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal /= np.linalg.norm(normal,axis=-1,keepdims=True)
    for suffix, data in [('color',color),('orm',255*packed),('normal',127.5*(1+normal))]:
        Image.fromarray(np.clip(data,0,255).astype('uint8')).save(
            TEXTURES/f'seal-{name}-{suffix}.jpg',quality=88,subsampling=0)


if __name__ == '__main__':
    for args in [('lotus',182,(88,90,86)), ('plume',215,(78,96,94)), ('cinder',369,(96,78,72))]:
        encode(*args)
