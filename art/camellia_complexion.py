"""Bake registered pore, lip and sebum variation for the wayfarer's face atlas."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

folder = Path(__file__).resolve().parents[1] / "native/Art/Wayfarer"
size = 2048
face = (
    Image.open(folder / "camellia-face.jpg")
    .convert("RGB")
    .resize((size, size), Image.Resampling.LANCZOS)
)
y, x = np.indices((size, size), dtype=np.float32) / size
rng = np.random.default_rng(26401)


def oval(cx, cy, rx, ry):
    return np.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2))


def blur(field, radius):
    pixels = Image.fromarray(np.round(field * 255).clip(0, 255).astype("uint8"))
    return (
        np.asarray(pixels.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32)
        / 255
    )


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


skin = smooth(2.5 * (oval(0.5, 0.52, 0.235, 0.28) - 0.12))
nose = oval(0.50, 0.572, 0.052, 0.073)
brow = oval(0.50, 0.355, 0.105, 0.12)
cheek = oval(0.373, 0.550, 0.071, 0.070) + oval(0.631, 0.550, 0.071, 0.070)
# The source diffuse separates vermilion from adjoining skin even at the corners.
rgb = np.asarray(face, dtype=np.float32) / 255
lip = smooth((rgb[:, :, 0] - rgb[:, :, 1] - 0.13) / 0.145) * smooth(
    2.1 * (oval(0.50, 0.692, 0.083, 0.030) - 0.25)
)
lid = oval(0.37, 0.449, 0.071, 0.031) + oval(0.63, 0.449, 0.071, 0.031)
# Local high frequencies only. Large shapes and shadows stay in the mesh and lighting.
luma = np.asarray(face.convert("L"), dtype=np.float32) / 255
detail = luma - blur(luma, 3.2)
seeds = (rng.random((size, size)) < 0.07).astype(np.float32)
pores = blur(seeds, 0.78) - blur(seeds, 2.1)
amount = (0.45 + 0.55 * cheek + 0.65 * nose) * (1 - 0.72 * lid)
fold = np.cos(
    2 * np.pi * (x * 172 + 0.42 * np.sin(25 * y + 8 * x) + 0.32 * np.sin(82 * x))
)
height = skin * (
    (2.1 * detail - 1.65 * pores * amount) * (1 - lip)
    - 0.20 * lip * np.maximum(fold, 0) ** 6
)
dv, du = np.gradient(height)
vectors = np.stack((-du, -dv, np.ones_like(du)), axis=-1)
vectors /= np.sqrt(np.sum(vectors * vectors, axis=-1, keepdims=True))
Image.fromarray(np.uint8(np.round(127.5 * (vectors + 1)))).save(
    folder / "CamelliaSkinNormal.png", optimize=True
)
rough = 0.55 + skin * (
    -0.12 * nose
    - 0.075 * brow
    - 0.04 * lid
    + 0.026 * cheek
    - 0.16 * lip
    + 0.12 * pores
    - 0.5 * detail
)
Image.fromarray(np.uint8(np.round(255 * np.clip(rough, 0.29, 0.68)))).save(
    folder / "CamelliaSkinRough.png", optimize=True
)
