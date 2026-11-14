"""Paint a continuous ink landscape across the six silk screens of a road lantern."""

from math import cos, exp, sin, tau
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw, ImageOps


def paint(source, target):
    width, height = 1536, 512
    rng = Random(5341)
    silk = (
        Image.open(source)
        .convert("L")
        .resize((width, height), Image.Resampling.BICUBIC)
    )
    silk = ImageOps.colorize(silk, (119, 76, 47), (245, 209, 151))
    wash = Image.new("RGBA", silk.size)
    brush = ImageDraw.Draw(wash)
    for layer, base, rise, tint in [
        (0, 0.62, 0.28, (95, 94, 80, 70)),
        (1, 0.72, 0.24, (80, 85, 79, 105)),
        (2, 0.87, 0.15, (69, 73, 63, 145)),
    ]:

        def ridge(x):
            a = tau * x / width
            return int(
                height
                * (
                    base
                    - rise * abs(sin(3 * a + layer) + 0.3 * sin(7 * a + layer))
                    + 0.02 * cos(19 * a + layer)
                )
            )

        edge = [(x, ridge(x)) for x in range(0, width + 1, 3)]
        brush.polygon(edge + [(width, height), (0, height)], fill=tint)
        for _ in range(60):
            x = rng.randrange(width)
            y = ridge(x) + rng.randrange(2, 21)
            brush.line(
                [(x, y), (x - 6, y + 8), (x - 12, y + rng.randrange(15, 30))],
                fill=(*tint[:3], tint[3] // 2),
                width=2,
            )
    # Fine pine branch tiers climb the near ridge. Each tree has its own lean.
    for x, floor, tall in [
        (51, 455, 93),
        (93, 460, 54),
        (370, 441, 75),
        (997, 423, 98),
        (1030, 439, 63),
        (1390, 439, 70),
    ]:
        lean = rng.uniform(-0.15, 0.18)
        tip = (x + lean * tall, floor - tall)
        brush.line([(x, floor), tip], fill=(48, 54, 48, 190), width=3)
        for k in range(8):
            t = 0.13 + 0.10 * k
            mid = x + lean * tall * t
            y = floor - tall * t
            for side in (-1, 1):
                span = side * tall * (0.28 * (1 - t) + 0.025) * rng.uniform(0.75, 1.15)
                brush.polygon(
                    [
                        (mid, y - 6),
                        (mid + span, y - 4),
                        (mid + span * 1.13, y - 11),
                        (mid + span * 0.60, y + 2),
                        (mid, y + 4),
                    ],
                    fill=(52, 61, 50, 166),
                )
    for x, y in [(183, 116), (200, 110), (812, 140), (827, 135), (1213, 99)]:
        brush.line(
            [(x - 5, y - 2), (x, y + 1), (x + 6, y - 4)],
            fill=(81, 68, 54, 150),
            width=2,
        )
    # The paper darkens towards the timber sockets above and below the flame.
    silk = Image.alpha_composite(silk.convert("RGBA"), wash).convert("RGB")
    pixels = silk.load()
    for y in range(height):
        for x in range(width):
            v = y / height
            warm = exp(-(((v - 0.56) / 0.44) ** 2)) * (
                0.90 - 0.10 * cos(tau * 6 * x / width)
            )
            r, g, b = pixels[x, y]
            pixels[x, y] = (
                int(r * (0.80 + 0.20 * warm)),
                int(g * (0.65 + 0.29 * warm)),
                int(b * (0.61 + 0.25 * warm)),
            )
    silk.save(target, quality=92, subsampling=0)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    paint(
        root / "public/art/belfry-paper.jpg", root / "native/Art/LanternLandscape.jpg"
    )
