"""Render two pine boughs into the UV columns used by the mountain-pine meshes."""

import io
from math import cos, hypot, pi, sin
from random import Random

from PIL import Image, ImageDraw


def needle_atlas():
    rng = Random(1337)
    # Keep the hidden colour close to a needle tip to avoid black mip fringes.
    img = Image.new("RGBA", (1024, 1024), (75, 95, 70, 0))
    draw = ImageDraw.Draw(img)

    def needle(x, y, dx, dy, color, width):
        length = hypot(dx, dy)
        nx, ny = -dy / length * width, dx / length * width
        bend = rng.uniform(-0.10, 0.10)
        mx, my = x + dx * 0.55 - dy * bend, y + dy * 0.55 + dx * bend
        draw.polygon(
            [
                (x + nx * 0.48, y + ny * 0.48),
                (mx + nx, my + ny),
                (x + dx, y + dy),
                (mx - nx * 0.78, my - ny * 0.78),
                (x - nx * 0.48, y - ny * 0.48),
            ],
            fill=(*color, 255),
        )

    def twig(x, y, dx, dy, length):
        # Individual fascicles fan off the last season's growth.
        shaft = rng.uniform(0.65, 0.85)
        tx, ty = x + dx * shaft, y + dy * shaft
        draw.line(
            [(x, y), (tx, ty), (x + dx, y + dy)], fill=(130, 103, 68, 255), width=4
        )
        axis = hypot(dx, dy)
        fx, fy = dx / axis, dy / axis
        for j in range(16):
            t = 0.27 + 0.73 * (j + rng.random()) / 16
            cx, cy = x + dx * t, y + dy * t
            for side in (-1, 1):
                slant = side * rng.uniform(0.20, 1.20)
                reach = length * rng.uniform(0.64, 1.25) * (1.13 - 0.23 * t)
                shade = rng.uniform(0.77, 1.16) * (0.85 + 0.20 * t)
                color = tuple(int(c * shade) for c in (94, 119, 80))
                for s in (slant, slant + side * 0.15):
                    needle(
                        cx,
                        cy,
                        (fx * cos(s) - fy * sin(s)) * reach,
                        (fy * cos(s) + fx * sin(s)) * reach,
                        color,
                        rng.uniform(1.0, 1.65),
                    )

    for column in range(2):

        def stem(t):
            return column * 512 + 251 + 20 * sin(
                3 * t + column
            ) - 11 * t, 1000 - 920 * t

        draw.line([stem(i / 36) for i in range(37)], fill=(102, 78, 49, 255), width=7)
        for i in range(11):
            for side in (-1, 1):
                t = 0.045 + i * 0.081 + (0.020 if side > 0 else 0)
                x, y = stem(t)
                reach = (
                    (157 + 25 * sin(pi * t)) * (1 - 0.50 * t) * rng.uniform(0.80, 1.04)
                )
                dx, dy = side * reach, -reach * rng.uniform(0.55, 0.91)
                draw.line(
                    [(x, y), (x + dx * 0.55, y + dy * 0.42), (x + dx, y + dy)],
                    fill=(117, 90, 57, 255),
                    width=5,
                )
                for f in (0.42, 0.72, 0.90):
                    cx, cy = x + dx * f, y + dy * f
                    tilt = rng.uniform(0.61, 1.23)
                    twig(cx, cy, side * 30 * tilt, -31 / tilt, 35 - 8 * t)
                twig(x + dx * 0.87, y + dy * 0.87, side * 30, -24, 43 - 12 * t)
        x, y = stem(0.92)
        twig(x, y, 3, -64, 45)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


if __name__ == "__main__":
    from pathlib import Path

    (Path(__file__).resolve().parents[1] / "Art" / "PineFascicles.png").write_bytes(
        needle_atlas()
    )
