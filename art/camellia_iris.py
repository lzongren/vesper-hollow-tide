"""Bake the pigment beneath the swordswoman's clear cornea."""

from pathlib import Path

import numpy as np
from PIL import Image

size = 512
y, x = (np.indices((size, size)) - (size - 1) / 2) / 72
r, theta = np.hypot(x, y), np.arctan2(y, x)
rng = np.random.default_rng(4207)
grain = rng.normal(0, 0.018, r.shape)
fiber = (
    0.20 * np.sin(79 * theta + 3 * np.sin(11 * theta) + 8 * r)
    + 0.24 * np.sin(103 * theta - 12 * r)
    + 0.26 * np.sin(31 * theta + 5 * r)
)
warm = np.exp(-(((r - 0.60) / 0.24) ** 2))
iris = (
    np.array([88, 60, 42])
    + warm[..., None] * [25, 13, 3]
    + (fiber + grain)[..., None] * [34, 24, 16]
)


def mix(a, b, weight):
    t = np.clip(weight, 0, 1)[..., None]
    return a * (1 - t) + b * t


iris = mix(iris, np.array([40, 33, 30]), (r - 0.83) / 0.14)
iris = mix(iris, np.array([19, 17, 17]), (0.44 - r) / 0.08)
sclera = np.array([220, 207, 196]) - np.minimum(abs(x), 3)[..., None] * [4, 6, 6]
sclera += (grain * 26)[..., None]
color = mix(sclera, iris, (1.02 - r) / 0.06)
color *= (1 - 0.105 * np.clip((-y - 0.10) / 0.85, 0, 1))[..., None]
dest = Path(__file__).resolve().parents[1] / "native/Art/Wayfarer/camellia-eye.jpg"
Image.fromarray(np.uint8(color.clip(0, 255))).save(dest, quality=97, subsampling=0)
