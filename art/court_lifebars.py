"""Render the knotted gold rails, cinnabar lacquer and engraved boss nameplates."""

import argparse
from pathlib import Path
from math import cos, pi, sin
from PIL import Image, ImageDraw, ImageFont

SCALE = 3
GOLD = (177, 137, 78, 255)
LIGHT = (234, 205, 152, 255)
UMBER = (45, 27, 24, 245)
BOSS_NAMES = {"Bellwarden": "守鐘人", "VeiledHeron": "白鷺", "CinderSaint": "灰燼聖徒"}


def render(folder, typeface):
    folder.mkdir(parents=True, exist_ok=True)

    def sheet(w, h):
        return Image.new("RGBA", (w * SCALE, h * SCALE))

    def pt(x, y):
        return (round(x * SCALE), round(y * SCALE))

    def path(d, points, color, weight=1):
        d.line(
            [pt(*p) for p in points],
            fill=color,
            width=max(1, round(weight * SCALE)),
            joint="curve",
        )

    def poly(d, points, color):
        d.polygon([pt(*p) for p in points], fill=color)

    def bloom(d, x, y, scale):
        # Five overlapping magnolia petals are cut into an ink-dark seal.
        for j in range(5):
            a = j * 2 * pi / 5 - pi / 2
            points = []
            for k in range(41):
                t = pi * 2 * k / 40
                r = scale * (0.44 + 0.39 * cos(t))
                w = scale * 0.235 * sin(t) * (1 + 0.25 * cos(t))
                points.append(
                    (x + r * cos(a) - w * sin(a), y + r * sin(a) + w * cos(a))
                )
            poly(d, points, (105, 75, 48, 255))
            path(d, points, LIGHT, 0.9)
            path(
                d,
                [
                    (x + scale * 0.22 * cos(a), y + scale * 0.22 * sin(a)),
                    (x + scale * 0.63 * cos(a), y + scale * 0.63 * sin(a)),
                ],
                GOLD,
                0.7,
            )
        d.ellipse([pt(x - 1.6, y - 1.6), pt(x + 1.6, y + 1.6)], fill=LIGHT)

    for kind, w, h, left, right, mid in [
        ("player", 266, 42, 39, 257, 21),
        ("boss", 640, 32, 16, 624, 16),
    ]:
        im = sheet(w, h)
        d = ImageDraw.Draw(im)
        rail = [
            (left - 10, mid),
            (left - 2, mid - 6),
            (right + 2, mid - 6),
            (right + 9, mid),
            (right + 2, mid + 6),
            (left - 2, mid + 6),
        ]
        poly(d, rail, UMBER)
        path(d, rail + [rail[0]], GOLD, 1.25)
        path(d, [(left, mid - 4.5), (right, mid - 4.5)], LIGHT, 0.65)
        for x, side in ((left, -1), (right, 1)):
            for k in range(2):
                path(
                    d,
                    [
                        (x - side * 4, mid - 5 - k * 2),
                        (x + side * (6 + k * 2), mid - 5 - k * 2),
                        (x + side * (11 + k * 2), mid),
                        (x + side * (6 + k * 2), mid + 5 + k * 2),
                        (x - side * 4, mid + 5 + k * 2),
                    ],
                    GOLD,
                    0.65,
                )
        if kind == "player":
            x, y = 20, 21
            frame = [(x, y - 19), (x + 19, y), (x, y + 19), (x - 19, y)]
            poly(d, frame, (34, 38, 37, 245))
            path(d, frame + [frame[0]], LIGHT, 1)
            bloom(d, x, y, 16)
        im.save(folder / (kind + "-rail.png"))
        fill = sheet(right - left, 8)
        d = ImageDraw.Draw(fill)
        for y in range(fill.height):
            t = y / (fill.height - 1)
            color = (round(160 - 58 * t), round(54 - 33 * t), round(44 - 25 * t), 255)
            d.line([(0, y), (fill.width, y)], fill=color)
        d.line([(0, 1), (fill.width, 1)], fill=(214, 116, 84, 255), width=2)
        fill.save(folder / (kind + "-lacquer.png"))
    chip = Image.new("RGBA", (2, 8 * SCALE))
    pixels = chip.load()
    for y in range(chip.height):
        t = y / (chip.height - 1)
        for x in range(chip.width):
            pixels[x, y] = (int(211 - 36 * t), int(163 - 44 * t), int(95 - 28 * t), 255)
    chip.save(folder / "damage.png")
    font = ImageFont.truetype(str(typeface), 26 * SCALE)
    for key, name in BOSS_NAMES.items():
        im = sheet(320, 42)
        d = ImageDraw.Draw(im)
        widths = [d.textlength(c, font=font) for c in name]
        spacing = 3 * SCALE
        x = (im.width - sum(widths) - spacing * (len(name) - 1)) / 2
        for char, width in zip(name, widths):
            pos = (round(x), round(im.height / 2))
            d.text(
                (pos[0] + 2, pos[1] + 3),
                char,
                font=font,
                anchor="lm",
                fill=(26, 16, 13, 255),
                stroke_width=3,
                stroke_fill=(26, 16, 13, 245),
            )
            d.text(
                pos,
                char,
                font=font,
                anchor="lm",
                fill=(247, 226, 186, 255),
                stroke_width=1,
                stroke_fill=(104, 72, 47, 255),
            )
            x += width + spacing
        im.save(folder / (key + ".png"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "typeface", type=Path, help="Chinese calligraphic or serif font"
    )
    args = parser.parse_args()
    render(Path(__file__).resolve().parents[1] / "native/Art/Lifebars", args.typeface)
