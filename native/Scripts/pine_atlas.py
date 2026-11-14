"""Generate colour and cutout for a pair of original mountain-pine sprays."""

import io
import math
from random import Random

from PIL import Image, ImageDraw


def needle_atlas():
    rng = Random(1337)
    image = Image.new("RGBA", (1024, 1024), (58, 86, 66, 0))
    draw = ImageDraw.Draw(image)

    def stroke(a, b, width, color):
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy)
        nx, ny = -dy / d * width, dx / d * width
        draw.polygon([(a[0] + nx, a[1] + ny), (a[0] - nx, a[1] - ny), b], fill=color)

    def draw_spray(column):
        base = column * 512

        def pt(t):
            return (
                base + 244 + 39 * math.sin(t * 2.3 + column) - 10 * t,
                1000 - 937 * t,
            )

        draw.line([pt(i / 35) for i in range(36)], fill=(89, 66, 43, 255), width=13)
        for n in range(24):
            t = 0.04 + 0.89 * n / 24
            ax, ay = pt(t)
            for side in (-1, 1):
                length = (
                    (60 + 138 * math.sin(0.35 + t * math.pi))
                    * (1 - t * 0.39)
                    * rng.uniform(0.8, 1.03)
                )
                bx = ax + side * length
                by = ay - rng.uniform(0.53, 0.95) * length
                shade = rng.uniform(0.79, 1.15)
                draw.line([(ax, ay), (bx, by)], fill=(92, 79, 50, 255), width=6)
                for j in range(29):
                    u = (j + rng.random()) / 30
                    x = ax + (bx - ax) * u
                    y = ay + (by - ay) * u
                    for direction in (-1, 1):
                        reach = rng.uniform(23, 45) * (1.1 - u * 0.24)
                        dx = side * (0.55 + direction * 0.64) * reach
                        dy = -(0.8 - direction * 0.44) * reach
                        bright = rng.uniform(0.76, 1.2) * shade * (0.9 + 0.14 * u)
                        col = tuple(
                            min(255, int(k * bright)) for k in (75, 105, 71)
                        ) + (255,)
                        stroke((x, y), (x + dx, y + dy), rng.uniform(2.3, 4.0), col)
        for j in range(55):
            x, y = pt(0.91 + j / 620)
            stroke(
                (x, y),
                (x + rng.uniform(-30, 30), y - rng.uniform(18, 37)),
                2.8,
                (109, 132, 86, 255),
            )

    for column in range(2):
        draw_spray(column)
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
