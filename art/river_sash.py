"""Weave a narrow celadon river-and-cloud brocade on a plum silk ground."""

import math
from pathlib import Path
from PIL import Image, ImageDraw


def weave(output):
    width, height = 384, 1536
    im = Image.new("RGB", (width, height))
    pix = im.load()
    for y in range(height):
        for x in range(width):
            satin = 3 * math.sin(2 * math.pi * (x - y * 0.16) / 5) + 2 * math.cos(
                2 * math.pi * y / 3.5
            )
            fold = 7 * math.sin(2 * math.pi * x / width) + 3 * math.cos(
                5 * x / width + 2 * y / height
            )
            pix[x, y] = tuple(round(c + satin + fold) for c in (86, 38, 47))
    d = ImageDraw.Draw(im)

    def couch(points, colour, size):
        d.line(points, fill=(52, 34, 36), width=size + 3, joint="curve")
        d.line(points, fill=colour, width=size, joint="curve")
        for i in range(2, len(points) - 1, 6):
            x, y = points[i]
            d.line((x - 2, y, x + 2, y + 1), fill=(211, 178, 126), width=1)

    for x in (12, 22, 362, 372):
        couch([(x, y) for y in range(0, height, 3)], (190, 153, 99), 3)
    for k in range(6):
        base = 90 + k * 248
        flip = (-1) ** k
        for lane in range(3):
            pts = []
            for i in range(130):
                t = i / 129
                x = 192 + flip * (112 * math.sin(2 * math.pi * t - 0.8) + 7 * lane)
                y = base + 176 * t + 8 * lane
                pts.append((x, y))
            couch(pts, ((173, 144, 101), (100, 157, 143), (202, 170, 121))[lane], 4)
        for side in (-1, 1):
            pts = []
            for i in range(94):
                t = i / 93
                a = t * math.pi * 1.72
                radius = 40 * (1 - t) + 4
                pts.append(
                    (
                        192 + side * (77 + radius * math.cos(a)),
                        base + 52 + radius * math.sin(a),
                    )
                )
            couch(pts, (164, 138, 94), 4)
    im.save(output, quality=94, subsampling=0)


if __name__ == "__main__":
    weave(Path(__file__).resolve().parents[1] / "native/Art/Wayfarer/river-sash.jpg")
