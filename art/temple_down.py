"""Bake four sideburn wisps for Haitang: U selects a card and V runs root to tip."""

from pathlib import Path

import numpy as np
from PIL import Image


DEST = Path(__file__).resolve().parents[1] / "native/Art/Wayfarer/temple-down.png"
WIDTH = 256
HEIGHT = 1024


def paint_strip(seed, bend, roots, long_count, soften_crossing=False):
    """Composite individual hair footprints in linear coverage and straight sRGB."""
    rng = np.random.default_rng(seed)
    alpha = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    pigment = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    y = (np.arange(HEIGHT) + 0.5) / HEIGHT
    x = (np.arange(WIDTH) + 0.5)[None, :]

    # Families share a curl without terminating as one pointed lock. Short down
    # grows between these families; only a handful of fibers reach the cheek.
    for index, root in enumerate(roots):
        bow = bend + rng.uniform(-0.045, 0.045)
        drift = rng.uniform(-0.115, 0.115)
        count = (13, 11, 9)[index]
        for strand in range(count):
            is_long = strand < long_count[index]
            start_x = root + rng.normal(0, 0.067 if is_long else 0.079)
            start_x = np.clip(start_x, -0.37, 0.37)
            start = rng.uniform(0.004, 0.055)
            end = rng.uniform(0.68, 0.972) if is_long else rng.uniform(0.20, 0.72)
            # A long guide fiber keeps each wisp legible in distant mips.
            # Its companions break away along the shaft at different lengths.
            if strand == 0 and index == 0:
                end = rng.uniform(0.93, 0.972)
            elif strand == 0 and index == 1:
                end = rng.uniform(0.83, 0.90)
            row = (y > start) & (y < end)
            t = ((y[row] - start) / (end - start))[:, None]
            # Each strand moves through its family's arc at its own rate.
            # Leave the arc open at the end so stray fibers taper separately.
            swing = bow + rng.uniform(-0.04, 0.04)
            tip_offset = drift + rng.uniform(-0.16, 0.16)
            wave = rng.uniform(-0.043, 0.043)
            center = 0.5 + start_x + swing * np.sin(np.pi * t)
            center += tip_offset * t + wave * np.sin(2 * np.pi * t)
            center = center * WIDTH

            diameter = rng.uniform(1.65, 2.80) if is_long else rng.uniform(1.10, 2.30)
            opacity = rng.uniform(0.62, 0.86) if is_long else rng.uniform(0.38, 0.72)
            # Add the texel box variance to the soft strand footprint. This
            # preserves fractional coverage after the fiber tapers below a pixel.
            taper = (1 - t**1.8) ** 0.70
            sigma = diameter / 2.355 * taper
            variance = sigma**2 + 1 / 12
            dist = x - center
            coverage = (
                opacity * sigma / np.sqrt(variance) * np.exp(-0.5 * dist**2 / variance)
            )
            root_fade = np.clip(t / rng.uniform(0.035, 0.085), 0, 1)
            tip_fade = np.clip((1 - t) / 0.16, 0, 1)
            coverage *= root_fade**2 * (3 - 2 * root_fade) * tip_fade
            # The second family's long guide meets adjacent fibers near local
            # U=.68 on the fourth card. Ease just its shaft at that crossing.
            if soften_crossing and index == 1 and strand == 0:
                middle = np.clip(1 - ((y[row, None] - 0.44) / 0.20) ** 2, 0, 1)
                coverage *= 1 - 0.20 * middle**2 * (3 - 2 * middle)
            # Guard the UV gutter even for a strand that bows toward the edge.
            # Fade over several texels so no straight clipped edge can be seen.
            gutter = np.clip((np.minimum(x, WIDTH - x) - 7) / 11, 0, 1)
            coverage *= gutter**2 * (3 - 2 * gutter)
            ink = rng.uniform(30, 53)
            color = np.array([ink * 1.06, ink * 0.88, ink * 0.79])
            visible = coverage[:, :, None]
            pigment[row] = color * visible + pigment[row] * (1 - visible)
            alpha[row] = coverage + alpha[row] * (1 - coverage)

    # Keep a matching transparent pigment in the gutters to avoid bright
    # fringes when Unreal filters RGB and opacity independently.
    straight = np.full_like(pigment, (41, 34, 31))
    np.divide(pigment, alpha[:, :, None], out=straight, where=alpha[:, :, None] > 1e-5)
    return np.uint8(np.rint(np.dstack([straight, 255 * alpha])).clip(0, 255))


def bake():
    strips = [
        paint_strip(910235, -0.080, (-0.17, 0.10, 0.18), (4, 2, 1)),
        paint_strip(436281, 0.065, (-0.22, 0.06, 0.21), (2, 1, 1)),
        paint_strip(631480, -0.045, (-0.16, -0.01, 0.19), (3, 1, 2)),
        paint_strip(
            292714, 0.105, (-0.20, -0.05, 0.13), (1, 3, 1), soften_crossing=True
        ),
    ]
    Image.fromarray(np.hstack(strips)).save(DEST, optimize=True)


if __name__ == "__main__":
    bake()
