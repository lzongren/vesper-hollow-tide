"""Bake hairline coverage and the swordswoman's hand-painted plum makeup."""

from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFilter

ART = Path(__file__).resolve().parents[1] / "native/Art/Wayfarer"


def complexion():
    face = Image.open(ART / "ruyi-face.jpg").convert("RGB")
    w, h = face.size
    wash = Image.new("RGBA", face.size)
    draw = ImageDraw.Draw(wash)
    for x in (0.315, 0.700):
        draw.ellipse(
            ((x - 0.068) * w, 0.531 * h, (x + 0.068) * w, 0.607 * h),
            fill=(152, 58, 60, 22),
        )
    face = Image.alpha_composite(
        face.convert("RGBA"), wash.filter(ImageFilter.GaussianBlur(0.019 * w))
    )
    # The old portrait supplies natural lip texture. A muted carmine glaze
    # follows its vermilion border without painting over the mouth opening.
    pixels = face.load()
    for y in range(int(0.690 * h), int(0.810 * h)):
        for x in range(int(0.395 * w), int(0.622 * w)):
            r, g, b, a = pixels[x, y]
            mask = max(0, min(1, ((r - g) / max(r, 1) - 0.32) * 6))
            falloff = math.exp(
                -(((x / w - 0.51) / 0.084) ** 4) - ((y / h - 0.754) / 0.048) ** 4
            )
            k = mask * falloff
            pixels[x, y] = (
                round(r * (1 + 0.050 * k)),
                round(g * (1 - 0.23 * k)),
                round(b * (1 - 0.10 * k)),
                a,
            )
    stamp = Image.new("RGBA", face.size)
    brush = ImageDraw.Draw(stamp)
    # Five hand-cut petals and a gilt centre, above the glabella.
    for n in range(5):
        theta = math.tau * n / 5 - math.pi / 2
        shape = []
        for i in range(53):
            a = math.tau * i / 52
            along = 0.0058 + 0.0065 * math.cos(a)
            across = 0.0040 * math.sin(a) * (0.65 + 0.35 * math.cos(a))
            shape.append(
                (
                    (0.508 + along * math.cos(theta) - across * math.sin(theta)) * w,
                    (0.323 + along * math.sin(theta) + across * math.cos(theta)) * h,
                )
            )
        brush.polygon(shape, fill=(134, 42, 43, 184))
    brush.ellipse(
        (0.5066 * w, 0.3216 * h, 0.5094 * w, 0.3244 * h), fill=(218, 170, 105, 198)
    )
    Image.alpha_composite(
        face, stamp.filter(ImageFilter.GaussianBlur(0.00029 * w))
    ).convert("RGB").save(ART / "plum-face.jpg", quality=96, subsampling=0)


def fringe():
    rng = random.Random(7430)
    w, h = 1024, 512
    image = Image.new("RGBA", (w, h), (47, 34, 27, 0))
    draw = ImageDraw.Draw(image)
    for _ in range(510):
        base = rng.uniform(0, w)
        cluster = math.sin(base / w * math.tau * 4 + 0.8)
        tip = h * (0.54 + 0.12 * cluster + 0.29 * rng.random())
        sweep = w * (0.062 + 0.019 * cluster + 0.025 * rng.random())
        width = rng.uniform(0.38, 0.83)
        l = rng.uniform(0, 1)
        color = (round(23 + 29 * l), round(17 + 23 * l), round(15 + 18 * l), 230)
        left, right = [], []
        for i in range(23):
            t = i / 22
            x = base + sweep * (1 - math.cos(t * math.pi / 2))
            size = width * (1 - 0.92 * t * t)
            left.append((x - size, tip * t))
            right.append((x + size, tip * t))
        # Duplicate the border strands for a wrap-safe horizontally tiled atlas.
        points = left + right[::-1]
        for offset in (0, -w, w):
            draw.polygon([(x + offset, y) for x, y in points], fill=color)
    image.save(ART / "temple-strands.png")


if __name__ == "__main__":
    complexion()
    fringe()
