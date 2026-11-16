"""Bake two asymmetrical wind-pruned pines in metres. Requires Pillow for the spray atlas."""

import math
import sys
from pathlib import Path
from random import Random

from bind_pilgrim import Output, cross, unit
from pine_atlas import needle_atlas


def add(a, b):
    return tuple(i + j for i, j in zip(a, b))


def scale(a, k):
    return tuple(i * k for i in a)


def delta(a, b):
    return tuple(i - j for i, j in zip(a, b))


class Surface:
    def __init__(self):
        self.p = []
        self.n = []
        self.uv = []
        self.color = []
        self.faces = []

    def vertex(self, p, n, uv, color):
        i = len(self.p)
        self.p.append(p)
        self.n.append(n)
        self.uv.append(uv)
        self.color.append(color)
        return i

    def quad(self, a, b, c, d):
        self.faces.extend([(a,), (b,), (c,), (a,), (c,), (d,)])

    def primitive(self, glb, material):
        attrs = {
            "POSITION": glb.data(self.p, "VEC3", bounds=True),
            "NORMAL": glb.data(self.n, "VEC3"),
            "TEXCOORD_0": glb.data(self.uv, "VEC2"),
            "COLOR_0": glb.data(self.color, "VEC3"),
        }
        return {
            "attributes": attrs,
            "indices": glb.data(self.faces, "SCALAR", 5125),
            "material": material,
        }


def pine(glb, variant):
    rng = Random(8401 + variant)
    bark, leaf = Surface(), Surface()

    def tube(path, radii, sides):
        prev = None
        length = 0
        for j, p in enumerate(path):
            t = unit(delta(path[min(j + 1, len(path) - 1)], path[max(j - 1, 0)]))
            guide = (0, 0, 1) if abs(t[2]) < 0.91 else (1, 0, 0)
            u = unit(cross(t, guide))
            v = unit(cross(t, u))
            if j:
                length += math.dist(path[j - 1], p)
            ring = []
            for k in range(sides + 1):
                theta = 2 * math.pi * k / sides
                n = add(scale(u, math.cos(theta)), scale(v, math.sin(theta)))
                r = radii[j] * (1 + 0.065 * math.cos(3 * theta + 0.32 * j))
                ring.append(
                    bark.vertex(
                        add(p, scale(n, r)),
                        n,
                        (k / sides * 2.4, length / 1.8),
                        (0.70, 0.66, 0.57),
                    )
                )
            if prev:
                for k in range(sides):
                    bark.quad(prev[k], prev[k + 1], ring[k + 1], ring[k])
            prev = ring

    def spray(origin, heading, length, width, lift, tilt):
        forward = (math.cos(heading), 0, math.sin(heading))
        right = (-forward[2], 0, forward[0])
        col = rng.randrange(2)
        tint = rng.uniform(0.70, 1.06)
        prev = None
        for j in range(3):
            t = j / 2
            center = add(
                origin,
                add(
                    scale(forward, length * t),
                    (0, length * (lift * t + 0.15 * t * t), 0),
                ),
            )
            row = []
            for side in (-1, 0, 1):
                p = add(
                    center,
                    add(
                        scale(right, width * side),
                        (0, width * (tilt * side - 0.26 * abs(side)), 0),
                    ),
                )
                n = unit(add(scale(right, -tilt + 0.24 * side), (0, 1, 0)))
                uv = ((col + (side + 1) / 2) / 2, 1 - t)
                row.append(leaf.vertex(p, n, uv, (tint, tint, tint * 0.93)))
            if prev:
                for k in range(2):
                    leaf.quad(prev[k], prev[k + 1], row[k + 1], row[k])
            prev = row

    height = 10.6 + variant * 0.8

    def stem(t):
        return (
            0.5 * math.sin(t * 5.2 + variant) * t + 1.05 * t * t,
            t * height,
            0.55 * math.sin(t * 4.6) * t,
        )

    tube(
        [stem(i / 18) for i in range(19)],
        [0.31 * (1 - i / 18) ** 0.76 + 0.017 for i in range(19)],
        12,
    )
    for k in range(7):
        a = k * math.tau / 7 + rng.uniform(-0.23, 0.23)
        d = (math.cos(a), 0, math.sin(a))
        tube(
            [
                (0, 0.42, 0),
                add(scale(d, 0.52), (0, 0.15, 0)),
                add(scale(d, 1.04), (0, -0.05, 0)),
            ],
            [0.15, 0.125, 0.03],
            6,
        )

    def grow_branch(j):
        t = 0.20 + j * 0.79 / 39
        heading = j * 2.399 + variant + rng.uniform(-0.23, 0.23)
        front = (math.cos(heading), 0, math.sin(heading))
        across = (-front[2], 0, front[0])
        length = (3.8 * (1 - t) ** 0.55 + 0.28) * rng.uniform(0.75, 1.19)
        anchor = stem(t)

        def branch(u):
            return add(
                anchor,
                add(
                    scale(front, u * length),
                    add(
                        scale(across, 0.23 * math.sin(3 * u + j) * u),
                        (0, length * (0.16 * u - 0.29 * math.sin(math.pi * u)), 0),
                    ),
                ),
            )

        tube(
            [branch(i / 6) for i in range(7)],
            [0.105 * (1 - i / 6) ** 0.86 + 0.012 for i in range(7)],
            7,
        )
        if j in (0, 3, 6):
            return
        for k in range(8):
            frac = 0.22 + 0.74 * k / 8
            for side in (-1, 1):
                a = heading + side * rng.uniform(0.55, 1.28)
                reach = (
                    (1.13 - 0.56 * frac)
                    * min(1, length / 2.1)
                    * rng.uniform(0.81, 1.12)
                )
                axis = (math.cos(a), 0, math.sin(a))
                start = branch(frac)
                mid = add(start, add(scale(axis, reach * 0.54), (0, 0.08, 0)))
                end = add(start, add(scale(axis, reach), (0, 0.22, 0)))
                tube([start, mid, end], [0.029, 0.017, 0.005], 4)
                for off, turn in [(mid, -0.40), (mid, 0.40), (end, 0.0)]:
                    spray(
                        off,
                        a + turn,
                        rng.uniform(0.62, 1.02) * min(1, length / 1.5),
                        rng.uniform(0.25, 0.41),
                        rng.uniform(0.03, 0.39),
                        rng.uniform(-0.7, 0.7),
                    )

    for j in range(39):
        grow_branch(j)
    name = ["WindPine", "RidgePine"][variant]
    glb.doc["meshes"].append(
        {"name": name, "primitives": [bark.primitive(glb, 0), leaf.primitive(glb, 1)]}
    )
    glb.doc["nodes"].append({"name": name, "mesh": variant})
    glb.doc["scenes"][0]["nodes"].append(variant)


def bake(textures, out):
    g = Output()
    g.doc.update(nodes=[], meshes=[], scenes=[{"nodes": []}])
    g.doc["asset"]["generator"] = "Vesper mountain pines"
    brown = g.image(
        (textures / "wood-color.jpg").read_bytes(), "image/jpeg", "Bark grain"
    )
    normal = g.image(
        (textures / "wood-normal.jpg").read_bytes(), "image/jpeg", "Bark ridges"
    )
    spray = g.image(needle_atlas(), "image/png", "Pine needle sprays")
    g.doc["materials"] = [
        {
            "name": "Mountain bark",
            "pbrMetallicRoughness": {
                "baseColorTexture": brown,
                "metallicFactor": 0,
                "roughnessFactor": 0.89,
            },
            "normalTexture": normal,
        },
        {
            "name": "Pine needles",
            "doubleSided": True,
            "alphaMode": "MASK",
            "alphaCutoff": 0.34,
            "pbrMetallicRoughness": {
                "baseColorTexture": spray,
                "metallicFactor": 0,
                "roughnessFactor": 0.83,
            },
        },
    ]
    for i in range(2):
        pine(g, i)
    g.save(out)


if __name__ == "__main__":
    bake(Path(sys.argv[1]), Path(sys.argv[2]))
