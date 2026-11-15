"""Bake willow hair cards, the fitted eyelids and chestnut irises for the heroine."""

from math import pi, sin
from pathlib import Path
from random import Random

import numpy as np
from PIL import Image, ImageDraw

DEST = Path(__file__).resolve().parents[1] / "native/Art/Wayfarer/willow-locks.png"


def bake():
    rng = Random(1629)
    # Supersample fine strands so the MSAA-independent opacity mask has soft mips.
    canvas = Image.new("RGBA", (2048, 2048), (36, 29, 26, 0))
    draw = ImageDraw.Draw(canvas)
    for group in range(4):
        for i in range(560):
            root = rng.uniform(-1, 1)
            end = rng.uniform(0.65, 0.985) - abs(root) ** 2 * 0.11
            phase = rng.uniform(-0.55, 0.55)
            stray = rng.random() < 0.12
            thickness = rng.uniform(0.9, 2.8)
            tone = rng.uniform(0, 0.8) + 0.15 * sin(19 * root)
            rgb = (int(29 + 40 * tone), int(24 + 33 * tone), int(23 + 27 * tone), 255)
            left, right = [], []
            for j in range(72):
                t = end * j / 71
                spread = (0.83 + 0.12 * sin(t * pi)) * (
                    1 - (0.59 if stray else 0.89) * t**1.65
                )
                x = group * 512 + 256 + 244 * root * spread
                x += (
                    19 * sin(6 * t + group) * t + 21 * sin(9 * t + 4 * root + phase) * t
                )
                radius = thickness * (1 - 0.87 * (j / 71) ** 2)
                left.append((x - radius, 2047 * t))
                right.append((x + radius, 2047 * t))
            draw.polygon(left + right[::-1], fill=rgb)
    canvas.resize((1024, 1024), Image.Resampling.LANCZOS).save(DEST)


def complexion_and_eyes():
    # Reduce the illumination baked below the nose and around the eyes so
    # their shape can respond to the moving light in the game.
    face = Image.open(DEST.with_name("plum-face.jpg")).convert("RGB")
    pixels = np.asarray(face).astype(np.float32) / 255
    y, x = np.mgrid[0 : face.height, 0 : face.width]
    x, y = x / face.width, y / face.height

    def oval(cx, cy, rx, ry):
        return np.exp(-(((x - cx) / rx) ** 2) - ((y - cy) / ry) ** 2)

    shadow = 0.35 * oval(0.508, 0.643, 0.071, 0.026)
    for cx in (0.374, 0.639):
        shadow += 0.18 * oval(cx, 0.500, 0.073, 0.032)
    target = np.array([0.82, 0.64, 0.53])
    pixels += np.maximum(0, target - pixels) * shadow[:, :, None]
    # Keep the photographed iris off the eyelids. The original projection
    # painted a second pupil on the lower lid in a three-quarter view.
    for cx in (0.379, 0.634):
        dx = (x - cx) / 0.058
        span = np.sqrt(np.maximum(0.0, 1 - dx**2))
        centre = 0.456 + (0.004 if cx < 0.5 else -0.004) * dx
        upper = y < centre
        radius = np.where(upper, 0.027, 0.031)
        mask = np.clip((span * radius + 0.002 - abs(y - centre)) / 0.004, 0, 1)
        mask *= np.clip((1 - abs(dx)) * 12, 0, 1)
        # Preserve a little of the neighbouring skin grain in the fold.
        sample_y = np.clip(
            np.where(
                upper, centre - 0.030 * span - 0.006, centre + 0.031 * span + 0.004
            )
            * face.height
            + (y - centre) * 0.24 * face.height,
            0,
            face.height - 1,
        ).astype(int)
        lid = pixels[sample_y, np.arange(face.width)[None, :]]
        pixels += (lid - pixels) * mask[:, :, None]
    # Follow the upper rim of the open mesh. A tapered brown lash line gives
    # the moving eyelid its edge in both neutral light and deep shadow.
    head_x = abs((x - 0.508) / 0.416)
    along = np.clip((head_x - 0.179) / 0.275, 0, 1)
    arc = np.maximum(0, np.sin(np.pi * along))
    lid_y = 7.265 + 0.030 * along + 0.054 * arc**0.78
    rim = 0.454 - (lid_y - 7.284) * np.where(lid_y < 7.284, 0.435, 0.342)
    liner = np.exp(-(((y - rim + 0.0008) / 0.0034) ** 2))
    pixels *= 1 - (0.56 * arc**0.5 * liner)[:, :, None]
    Image.fromarray(np.rint(pixels * 255).astype("uint8")).save(
        DEST.with_name("jade-face.jpg"), quality=97, subsampling=0
    )

    # A forward-facing iris map lives on each globe. Fit pigment from the
    # unobscured lower half of the original eye, mirroring around its centre.
    source = np.asarray(face).astype(np.float32)
    iy, ix = np.mgrid[0:512, 0:512]
    nx, ny = (ix - 255.5) / 77, (iy - 255.5) / 77
    radius = np.hypot(nx, ny)
    sx = np.rint((0.379 + nx * 0.023) * face.width).astype(int).clip(0, face.width - 1)
    sy = (
        np.rint((0.451 + abs(ny) * 0.022) * face.height)
        .astype(int)
        .clip(0, face.height - 1)
    )
    pigment = source[sy, sx]
    pupil = np.clip((0.38 - radius) / 0.065, 0, 1)[..., None]
    pigment = (1 - pupil) * pigment + pupil * np.array([18, 13, 13])
    limbus = np.clip((radius - 0.82) / 0.15, 0, 1)[..., None]
    pigment = (1 - limbus) * pigment + limbus * np.array([59, 44, 40])
    edge = np.clip((1.02 - radius) / 0.065, 0, 1)[..., None]
    sclera = np.array([196, 179, 168]) - 11 * np.minimum(abs(nx[..., None]) / 3, 1)
    # The top lid casts a soft contact shadow on the globe.
    shade = 1 - 0.18 * np.clip((-ny + 0.10) / 0.62, 0, 1)
    eye = (pigment * edge + sclera * (1 - edge)) * shade[..., None]
    Image.fromarray(np.uint8(eye)).save(DEST.with_name("chestnut-eye.jpg"), quality=97)


if __name__ == "__main__":
    bake()
    complexion_and_eyes()
