"""Bake a wrapping hairline whose opaque upper edge meets the combed scalp."""

import random
from math import cos, sin, tau
from pathlib import Path

from PIL import Image, ImageDraw

rng = random.Random(1792)
w, h = 1536, 384
im = Image.new("RGBA", (w, h), (31, 23, 21, 0))
draw = ImageDraw.Draw(im)
for i in range(4100):
    x = rng.random() * w
    phase = x / w * tau
    length = h * (
        0.42 + 0.12 * sin(3 * phase) + 0.12 * cos(8 * phase) + 0.31 * rng.random()
    )
    width = rng.uniform(0.43, 1.22)
    light = rng.random()
    rgb = tuple(round(a + light * b) for a, b in ((24, 29), (19, 21), (17, 17))) + (
        255,
    )
    borders = [[], []]
    for j in range(19):
        t = j / 18
        cx = x + (0.032 + 0.020 * sin(3 * phase)) * w * t * t
        r = width * (1 - 0.89 * t)
        for arr, edge in zip(borders, (-1, 1)):
            arr.append((cx + edge * r, t * length))
    for wrap in (-w, 0, w):
        draw.polygon(
            [(a + wrap, b) for a, b in borders[0] + borders[1][::-1]], fill=rgb
        )
# A fully covered band prevents a seam against the opaque scalp material.
alpha = im.getchannel("A")
for row in range(h // 3):
    floor = round(255 * (1 - row / (h // 3)) ** 0.48)
    band = alpha.crop((0, row, w, row + 1)).point(
        [max(value, floor) for value in range(256)]
    )
    alpha.paste(band, (0, row))
im.putalpha(alpha)
im.resize((1024, 256), Image.Resampling.LANCZOS).save(
    Path(__file__).resolve().parents[1] / "native/Art/Wayfarer/camellia-hairline.png"
)
