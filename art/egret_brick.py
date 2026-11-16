"""Bake the two-egret brick carving from the original sculpt guide and scanned stone."""

from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

out = Path(__file__).resolve().parents[1] / "native/Art/BellCourt"
source = Path(sys.argv[1])
size = (1792, 896)
image = (
    Image.open(out / "EgretSculpt.jpg")
    .convert("L")
    .resize(size, Image.Resampling.LANCZOS)
)
value = np.asarray(image, dtype=np.float32) / 255
# Reject the cast shadows and slow changes in the guide's gray backing.
height = np.clip((value - 0.412) / 0.44, 0, 1)
height = height**0.84
guide = Image.fromarray(np.uint8(np.round(height * 255)))
low = guide.filter(ImageFilter.GaussianBlur(2.1)).resize(
    (257, 129), Image.Resampling.LANCZOS
)
(out / "EgretHeight.pgm").write_bytes(b"P5\n257 129\n255\n" + low.tobytes())
coarse = np.asarray(low.resize(size, Image.Resampling.BICUBIC), dtype=np.float32) / 255
grain = Image.open(source / "rock-color.jpg").convert("L")
grain = grain.resize((596, 447), Image.Resampling.LANCZOS)
stone = np.tile(np.asarray(grain, dtype=np.float32) / 255, (3, 4))[: size[1], : size[0]]
field = stone - float(stone.mean())
# Only the relief below the geometry sampling scale enters the tangent normal.
residual = 0.077 * (height - coarse) + 0.00045 * field
dv, du = np.gradient(residual)
norm = np.stack((-du * size[0] / 5.42, dv * size[1] / 2.52, np.ones_like(du)), axis=-1)
norm /= np.sqrt(np.sum(norm**2, axis=-1, keepdims=True))
Image.fromarray(np.uint8(np.round((norm + 1) * 127.5))).save(
    out / "EgretChisel.jpg", quality=97, subsampling=0
)
tint = (
    np.array([111, 120, 118])
    + field[..., None] * [46, 46, 44]
    + height[..., None] * [11, 9, 7]
)
Image.fromarray(np.uint8(tint.clip(0, 255))).save(
    out / "EgretClay.jpg", quality=94, subsampling=0
)
