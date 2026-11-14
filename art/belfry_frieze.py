"""Paint the tide hall's paired dragons in worn mineral pigment on wood."""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
W, H = 1536, 384
rng = np.random.default_rng(923)
im = Image.new("RGB", (W,H), (45,78,76))
draw = ImageDraw.Draw(im)
gold = (211,170,95)
shade = (68,47,36)
red = (149,66,44)
blue = (54,90,111)
jade = (92,142,126)


def bezier(start, *arcs):
    pts = [start]
    for a,b,end in arcs:
        p = np.array([pts[-1],a,b,end])
        for u in np.linspace(0,1,28)[1:]:
            pts.append(tuple((1-u)**3*p[0]+3*u*(1-u)**2*p[1]+3*u*u*(1-u)*p[2]+u**3*p[3]))
    return pts


def brush(pts, width, color):
    draw.line(pts,fill=color,width=width,joint="curve")


def leaf(cx,cy,length,angle,width,fill):
    t = np.linspace(0,1,33)
    spine = np.stack([t*length,(t*t-t)*length*.36],axis=-1)
    bend = np.sin(np.pi*t)**.72 * width
    poly = np.concatenate([spine+np.stack([t*0,bend],axis=-1),
                           (spine-np.stack([t*0,bend],axis=-1))[::-1]])
    cs,sn=math.cos(angle),math.sin(angle)
    rot=np.array([[cs,sn],[-sn,cs]])
    pts=[tuple(p) for p in poly@rot+[cx,cy]]
    draw.polygon(pts,fill=fill);brush(pts,3,gold)
    brush([tuple(p) for p in spine@rot+[cx,cy]],2,shade)


# Scrolls and leaves fill the spaces around the dragon silhouette.
for i in range(13):
    x=55+i*59
    for cy,sign in [(76,1),(309,-1)]:
        a=np.linspace(-1.45,4.9,70)
        r=np.linspace(38,3,70)
        brush(list(zip(x+np.cos(a)*r,cy+sign*np.sin(a)*r)),4,(163,143,93))
        leaf(x+12,cy+sign*8,35,.4*sign,7,jade if i%2 else blue)

path=bezier((42,215),((88,247),(106,105),(201,153)),
            ((275,192),(216,288),(337,263)),((427,240),(372,108),(488,115)),
            ((559,114),(550,225),(628,190)))
brush(path,40,shade);brush(path,34,gold);brush(path,25,(61,113,95))
for i in range(3,len(path)-2,3):
    x,y=path[i];dx,dy=np.subtract(path[i+1],path[i-1]);ang=math.atan2(dy,dx)
    a=np.linspace(-1,1,9)
    pts=[(x+math.cos(ang)*(5-9*t*t)-math.sin(ang)*11*t,
          y+math.sin(ang)*(5-9*t*t)+math.cos(ang)*11*t) for t in a]
    brush(pts,3,(209,173,108))
for cx,cy,ang in [(161,149,-1.6),(213,165,-.6),(285,253,1.5),(364,240,-.1),(481,105,-1.45),(525,128,-.45)]:
    leaf(cx,cy,49,ang,10,red)
# A bent foreleg and three hooked claws.
leg=bezier((522,145),((526,194),(474,178),(484,226)),((492,245),(520,231),(535,233)))
brush(leg,15,shade);brush(leg,9,gold)
for i in range(3):
    brush(bezier((531,232),((559,231+i*5),(550,246+i*6),(566-i*4,244+i*7))),4,gold)
# Horns, jaws, eyelid, long whiskers and a tapered muzzle.
for k in range(3):leaf(601-k*9,169+k*8,74+k*7,-2.34-k*.21,12,red)
head=bezier((577,184),((580,149),(613,145),(634,156)),((644,165),(648,155),(652,176)),
            ((663,177),(688,167),(692,183)),((691,193),(675,202),(659,199)),
            ((648,217),(626,220),(612,210)),((595,213),(582,202),(577,184)))
draw.polygon(head,fill=(147,114,66));brush(head,5,gold)
for cx,cy in [(606,156),(622,154)]:
    brush(bezier((cx,cy),((cx+4,cy-28),(cx-27,cy-32),(cx-21,cy-60))),6,gold)
    brush([(cx-10,cy-31),(cx-1,cy-51)],4,gold)
brush(bezier((616,170),((626,156),(640,164),(644,172))),5,shade)
draw.ellipse((629,165,638,175),fill=(225,209,153));draw.ellipse((632,166,636,175),fill=shade)
brush(bezier((630,199),((649,187),(665,200),(682,189))),5,shade)
for x in [646,662]:draw.polygon([(x,194),(x+6,193),(x+3,202)],fill=(223,207,161))
for i in range(2):
    brush(bezier((680,183+i*5),((711,147+i*42),(690,116+i*122),(724,124+i*122))),4,gold)
# Mirror the beast and reserve the central pearl as a shared focal point.
im.paste(im.crop((0,0,W//2,H)).transpose(Image.Transpose.FLIP_LEFT_RIGHT),(W//2,0))
draw=ImageDraw.Draw(im)
for rad,col in [(42,shade),(39,gold),(33,red),(26,(113,61,49))]:
    draw.ellipse((768-rad,190-rad,768+rad,190+rad),fill=col)
for y in (12,24,46,H-46,H-24,H-12):
    draw.line((0,y,W,y),fill=gold if y in (24,H-24) else (106,72,54),width=5)
for x in range(-22,W,42):
    for y in (28,H-43):brush([(x,y+12),(x,y),(x+24,y),(x+24,y+9),(x+12,y+9)],3,(170,130,77))
pixels=np.asarray(im,dtype=np.float32)
def noise(w,h):
    a=Image.fromarray(rng.integers(0,255,(h,w),dtype=np.uint8))
    return np.asarray(a.resize((W,H),Image.Resampling.BICUBIC),dtype=np.float32)/255
pore=noise(280,9); aged=noise(128,38); grain=rng.normal(0,1,(H,W))
flaking=np.clip((.29-aged)*4 + .10*np.sin(np.arange(H)[:,None]*.82) + .055*grain,0,1)
pixels=pixels*(1-.61*flaking[...,None])+np.array([83,58,44])*.61*flaking[...,None]
pixels*= (.85+.2*pore+.045*grain)[...,None]
Image.fromarray(np.uint8(np.clip(pixels,0,255))).save(ROOT/'public/art/belfry-dragon-beam.jpg',quality=92,subsampling=0)


# Transmitted light across a bank of three screens. Back bars and slanting
# silhouettes soften with distance from the translucent paper.
from PIL import ImageFilter
pw,ph=512,512
shade=Image.new("L",(pw,ph))
ink=ImageDraw.Draw(shade)
def twig(x,y,a,length,level):
    ex=x+length*math.cos(a);ey=y+length*math.sin(a)
    ink.line([(x,y),(ex,ey)],fill=64+10*level,width=max(1,level*2))
    if level<=1:
        for side in [-1,1]:
            leaf_x=ex+side*6;leaf_y=ey+5
            ink.polygon([(ex,ey),(leaf_x+4,leaf_y+8),(leaf_x+side*12,leaf_y+15),(leaf_x-2,leaf_y+4)],fill=102)
        return
    for step in [-.55,.43]:
        twig(ex,ey,a+step+rng.uniform(-.18,.18),length*rng.uniform(.61,.81),level-1)
twig(541,539,-2.08,172,5)
dark=np.asarray(shade.filter(ImageFilter.GaussianBlur(4.6)),dtype=np.float32)/255
u,v=np.meshgrid(np.linspace(0,1,pw),np.linspace(0,1,ph))
glow=.26+.72*np.exp(-((u-.35)**2/.16+(v-.71)**2/.38))
grain=np.asarray(Image.fromarray(rng.integers(0,255,(160,34),dtype=np.uint8)).resize((pw,ph),Image.Resampling.BICUBIC),dtype=np.float32)/255
fold=1-.15*np.exp(-((v-.52)/.012)**2)
value=(glow+.12*grain+.035*rng.normal(0,1,(ph,pw)))*(1-.85*dark)*fold
rgb=np.stack([103+139*value,80+126*value,57+88*value],axis=-1)
Image.fromarray(np.uint8(np.clip(rgb,0,255))).save(ROOT/'public/art/belfry-paper.jpg',quality=89,subsampling=0)
