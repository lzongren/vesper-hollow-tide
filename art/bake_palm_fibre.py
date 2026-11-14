"""Bake the palm strips' authored linear vertex colours into a padded UV atlas.

Run on the original neutral export from export_pilgrim_mantle.ts. Pillow is
needed only by the authoring tool; the baked GLB ships with the native game.
"""

import io
import math
import sys
from pathlib import Path
from random import Random

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "native" / "Scripts"))
from bind_pilgrim import Glb, Output

STRIPS = 4 * sum(24 + 3 * course for course in range(4))
COLS, SIZE = 24, 1024
W, H, PAD = 42, 48, 3
ROWS = (STRIPS + COLS - 1) // COLS


def srgb(linear):
    value = (
        1.055 * max(linear, 0) ** (1 / 2.4) - 0.055
        if linear > 0.0031308
        else 12.92 * linear
    )
    return round(255 * max(0, min(1, value)))


def coord(x, y):
    return ((x + 0.5) / SIZE, (y + 0.5) / SIZE)


def bake(path):
    src = Glb(path)
    g = Output()
    g.doc = src.doc
    g.doc.setdefault("images", [])
    g.doc.setdefault("textures", [])
    g.binary = bytearray(src.binary[: g.doc["buffers"][0]["byteLength"]])
    candidates = [
        p
        for m in g.doc["meshes"]
        for p in m["primitives"]
        if "COLOR_0" in p["attributes"] and "TEXCOORD_0" not in p["attributes"]
    ]
    if len(candidates) != 1:
        raise ValueError(
            "Expected the unbaked palm mesh from the neutral mantle export"
        )
    prim = candidates[0]
    attrs = prim["attributes"]
    colors = src.values(attrs["COLOR_0"])
    if len(colors) != STRIPS * 21 + 3 * 362:
        raise ValueError("Palm strip or braid topology changed")
    faces = src.values(prim["indices"])
    for i in range(STRIPS):
        block = faces[i * 72 : (i + 1) * 72]
        if (
            min(a for (a,) in block) != 21 * i
            or max(a for (a,) in block) != 21 * i + 20
        ):
            raise ValueError("Unexpected strip winding or indexing")

    maps = [
        Image.new("RGB", (SIZE, SIZE), fill)
        for fill in [(102, 78, 51), (128, 128, 255), (255, 216, 0)]
    ]
    rgb, normal, orm = [im.load() for im in maps]
    uvs = []
    for i in range(STRIPS):
        left, top = i % COLS * W, i // COLS * H
        w, h = W - 2 * PAD - 1, H - 2 * PAD - 1
        for row in range(7):
            for col in range(3):
                uvs.append(coord(left + PAD + w * col / 2, top + PAD + h * row / 6))
        rng = Random(4163 + i)
        phase, sway, grain = (
            rng.random() * 6.28,
            rng.uniform(0.05, 0.23),
            rng.uniform(2.1, 4.5),
        )
        for y in range(H):
            v = min(1, max(0, (y - PAD) / h))
            ry = min(5, int(v * 6))
            fy = v * 6 - ry
            drift = sway * math.sin(v * 4.9 + phase)
            for x in range(W):
                u = min(1, max(0, (x - PAD) / w))
                cx = min(1, int(u * 2))
                fx = u * 2 - cx
                theta = math.tau * (grain * u + drift) + phase
                ridge = 0.5 + 0.5 * math.sin(theta)
                fine = math.sin(theta * 2.83 + 0.31 * math.sin(v * 32 + phase))
                grain_shade = 0.62 + 0.43 * ridge + 0.10 * fine
                base = 21 * i + 3 * ry + cx
                components = []
                for k in range(3):
                    a = colors[base][k] * (1 - fx) + colors[base + 1][k] * fx
                    b = colors[base + 3][k] * (1 - fx) + colors[base + 4][k] * fx
                    components.append(srgb((a * (1 - fy) + b * fy) * grain_shade))
                xy = left + x, top + y
                rgb[xy] = tuple(components)
                dx = 0.35 * math.cos(theta) + 0.12 * math.cos(theta * 2.83)
                dy = 0.045 * math.cos(4.9 * v + phase)
                length = math.sqrt(1 + dx * dx + dy * dy)
                normal[xy] = tuple(
                    round(127.5 * (1 + a / length)) for a in (-dx, -dy, 1)
                )
                orm[xy] = (255, round(191 + 39 * (1 - ridge)), 0)
    # Each continuous collar cord gets its own horizontal band, padded on each side.
    for thread in range(3):
        top = ROWS * H + thread * 28
        base = STRIPS * 21 + thread * 362
        for j in range(181):
            for edge in range(2):
                uvs.append(coord(4 + j * 1014 / 180, top + 4 + edge * 18))
        for y in range(28):
            for x in range(SIZE):
                ridge = 0.5 + 0.5 * math.cos(x * 0.24 + y * 0.6)
                xy = x, top + y
                rgb[xy] = tuple(srgb(k * (0.78 + 0.28 * ridge)) for k in colors[base])
                normal[xy] = (round(128 + 24 * math.sin(x * 0.24 + y * 0.6)), 128, 253)
                orm[xy] = (255, 210, 0)
    bindings = []
    for im, name in zip(
        maps, ["Palm bast colour", "Palm bast ridges", "Palm bast surface"]
    ):
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        bindings.append(g.image(buf.getvalue(), "image/png", name))
    attrs["TEXCOORD_0"] = g.data(uvs, "VEC2")
    del attrs["COLOR_0"]
    mat = g.doc["materials"][prim["material"]]
    mat["name"] = "Knotted palm bast"
    mat["pbrMetallicRoughness"].update(
        baseColorTexture=bindings[0],
        metallicRoughnessTexture=bindings[2],
        roughnessFactor=1,
    )
    mat["normalTexture"] = bindings[1]
    g.save(path)


if __name__ == "__main__":
    bake(Path(sys.argv[1]))
