"""Bake eight continuous limestone cliff faces using the existing court textures.

Each atlas cell wraps around one buttress. Rock joints, mineral wash and
vegetation follow its own drainage field. Requires NumPy and Pillow.
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 2048, 1024
BORDER = 6


def image(path):
    return np.asarray(Image.open(ROOT / path).convert("RGB"), dtype=np.float32) / 255


def surface(source, u, v):
    """Bilinear mirror sampling of the photographed detail."""
    h, w = source.shape[:2]
    x = (1 - np.abs(np.remainder(u, 2) - 1)) * (w - 1)
    y = (1 - np.abs(np.remainder(v, 2) - 1)) * (h - 1)
    ix, iy = x.astype(np.int32), y.astype(np.int32)
    dx, dy = (x - ix)[..., None], (y - iy)[..., None]
    nx, ny = np.minimum(ix + 1, w - 1), np.minimum(iy + 1, h - 1)
    return ((1 - dy) * ((1 - dx) * source[iy, ix] + dx * source[iy, nx]) +
            dy * ((1 - dx) * source[ny, ix] + dx * source[ny, nx]))


def bake_face(index, stone, fracture):
    rng = np.random.default_rng(8276 + index * 103)
    w, h = WIDTH - 2 * BORDER, HEIGHT - 2 * BORDER
    angle = np.arange(w, dtype=np.float32)[None, :] * (2 * np.pi / w)
    level = np.linspace(1, 0, h, dtype=np.float32)[:, None]

    def field(frequencies, vertical):
        weights = np.array([1 / 1.65 ** i for i in range(len(frequencies))])
        return sum(amp * np.sin(k * angle + rng.uniform(-3, 3) +
                                rng.uniform(-vertical, vertical) * level)
                   for amp, k in zip(weights, frequencies)) / weights.sum()

    runnel = field([3, 7, 13, 28], 2.9)
    tilt = field([1, 3, 7], 1.4)
    # Texture in overlapping sectors. Their centres wrap over the seam, while
    # their source locations, rock scales and dip directions differ.
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    sectors = 9
    for j in range(sectors):
        centre = j * 2 * np.pi / sectors
        delta = (angle - centre + np.pi) % (2 * np.pi) - np.pi
        arc = delta * sectors / (2 * np.pi)
        weight = np.maximum(0, 1 - np.abs(arc))
        weight = weight * weight * (3 - 2 * weight)
        cols = weight[0] > 0
        local = arc[:, cols]
        u = rng.uniform(0, 2) + local * rng.uniform(.57, .96) + .065 * runnel[:, cols]
        v = rng.uniform(0, 2) - level * rng.uniform(1.0, 1.8) + local * rng.uniform(-.25, .25)
        rgb[:, cols] += weight[:, cols, None] * surface(stone, u, v + .11 * tilt[:, cols])

    # Fine fissures from the court's stone surface. Draw them through the broad
    # calcite faces at a different scale; the original orange rock supplies relief.
    detail = surface(fracture, 2.7 * np.cos(angle) + .2 * runnel,
                     2.4 * level + 2.7 * np.sin(angle) + .14 * tilt)
    grain = np.mean(detail, axis=2)
    chalk = rgb.mean(axis=2)
    damp = np.clip((runnel + .12) * 1.6, 0, 1)
    streak = np.clip(.52 + field([13, 25, 42, 93], 3.0), 0, 1)
    ledge = .5 + .5 * np.cos((level + .14 * tilt) * (19 + index * .72))
    moss = np.clip((damp * .67 + ledge * .23 + level * .24 - .39) * 1.9, 0, .63)
    rgb *= (.91 + .24 * (grain - .5) - damp * (.06 + .17 * streak))[..., None]
    green = np.stack((.20 + .34 * chalk, .23 + .36 * chalk, .18 + .33 * chalk), axis=2)
    rgb += moss[..., None] * (green - rgb)
    output = np.uint8(np.clip(rgb * 255, 0, 255))
    return Image.fromarray(np.pad(np.pad(output, ((0, 0), (BORDER, BORDER), (0, 0)), mode="wrap"),
                                  ((BORDER, BORDER), (0, 0), (0, 0)), mode="edge"))


if __name__ == "__main__":
    stone = image("public/art/karst-limestone.jpg")
    fracture = image("public/textures/rock-color.jpg")
    atlas = Image.new("RGB", (WIDTH * 2, HEIGHT * 4))
    for index in range(8):
        atlas.paste(bake_face(index, stone, fracture), ((index % 2) * WIDTH, (index // 2) * HEIGHT))
    atlas.save(ROOT / "public/art/ridge-faces.jpg", quality=86, subsampling=1, optimize=True)
