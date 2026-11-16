"""Letter the belfry lintel right-to-left. Pass a CJK serif font as argv[1]."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

size = (1152, 352)
letters = Image.new("L", size)
ink = ImageDraw.Draw(letters)
font = ImageFont.truetype(sys.argv[1], 257, index=int(sys.argv[2]) if len(sys.argv)>2 else 0)
for x, char in zip((260, 576, 892), "殿潮鎮"):
    if not font.getmask(char).getbbox():
        raise ValueError(f"Font is missing the glyph {char}")
    ink.text((x, 179), char, font=font, fill=255, anchor="mm")
base = Image.new("RGB", size, "#201b16")
draw = ImageDraw.Draw(base)
for inset, color, width in [(9, "#91744c", 6), (25, "#605138", 3)]:
    draw.rounded_rectangle((inset,inset,size[0]-inset,size[1]-inset),radius=13,outline=color,width=width)
for x in (50,1101):
    for y in (48,303):
        draw.ellipse((x-6,y-6,x+6,y+6), fill="#9f8557")
base.paste("#080908",(0,0,*size),ImageChops.offset(letters,2,5).filter(ImageFilter.GaussianBlur(2)))
base.paste("#d8b277",(0,0,*size),letters)
base.paste("#f4d897",(0,0,*size),ImageChops.subtract(letters,ImageChops.offset(letters,1,3)))
base.save(Path(__file__).resolve().parents[1]/"public/art/belfry-plaque.jpg",quality=93,subsampling=0)
