"""Paint the wayfarer's forehead ornament and weave her knotted hair ribbons."""

from pathlib import Path
from math import cos, pi, sin, tau
from PIL import Image, ImageDraw
import numpy as np

ART = Path(__file__).resolve().parents[1] / "native/Art/Wayfarer"


def complexion():
    portrait = Image.open(ART / "camellia-face.jpg").convert("RGB")
    w, h = portrait.size
    # UV-space petal engraving. A supersampled transparent patch preserves pores
    # and the source registration on the rest of the face.
    scale = 5
    mask = Image.new("L", (180 * scale, 180 * scale))
    brush = ImageDraw.Draw(mask)
    for i in range(5):
        a = -pi / 2 + i * tau / 5
        outline = []
        for j in range(121):
            t = j * tau / 120
            r = 31 * (1 - cos(t))
            side = 16 * sin(t) * (0.68 + 0.32 * (1 - cos(t)))
            outline.append(
                (
                    (90 + r * cos(a) - side * sin(a)) * scale,
                    (90 + r * sin(a) + side * cos(a)) * scale,
                )
            )
        brush.polygon(outline, fill=205)
    brush.ellipse((84 * scale, 84 * scale, 96 * scale, 96 * scale), fill=35)
    size = (round(0.028 * w), round(0.040 * h))
    patch = mask.resize(size, Image.Resampling.LANCZOS)
    center = (round(0.504 * w), round(0.316 * h))
    stamp = Image.new("L", (w, h))
    stamp.paste(patch, (center[0] - size[0] // 2, center[1] - size[1] // 2))
    rgb = np.asarray(portrait, dtype=float)
    tint = rgb * np.array([0.78, 0.29, 0.34])
    amount = np.asarray(stamp)[..., None] / 255
    result = rgb * (1 - amount) + tint * amount
    Image.fromarray(np.uint8(result.clip(0, 255))).save(
        ART / "begonia-face.jpg", quality=97, subsampling=0
    )


def ribbon():
    w, h = 512, 1024
    y, x = np.mgrid[0:h, 0:w]
    # Warm silk warp, less saturated weft and faded couched double borders.
    warp = 0.047 * np.cos(tau * x / 3.7) + 0.027 * np.cos(tau * (y / 5 + x / 19))
    brocade = (
        0.065
        * np.cos(tau * (x / w * 6 + y / h * 4))
        * np.cos(tau * (x / w * 6 - y / h * 4))
    )
    dye = np.clip(np.array([124, 40, 58]) * (1 + warp + brocade)[..., None], 0, 255)
    silk = Image.fromarray(dye.astype("uint8"))
    pen = ImageDraw.Draw(silk)
    for s in (17, 28, w - 18, w - 29):
        pen.line((s, 0, s, h), fill=(183, 135, 84), width=3)
    for i in range(-1, 9):
        cy = i * h / 8
        for handed in (-1, 1):
            curve = []
            for k in range(121):
                t = k / 120
                u = handed * (33 + 71 * t) * sin(pi * t)
                curve.append((w / 2 + u, cy + 100 * t))
            pen.line(curve, fill=(153, 85, 85), width=5)
        pen.ellipse((w / 2 - 4, cy + 26, w / 2 + 4, cy + 34), fill=(194, 143, 96))
    silk.save(ART / "begonia-ribbon.jpg", quality=94, subsampling=0)


if __name__ == "__main__":
    complexion()
    ribbon()
