"""Generate a ground-rooted, two-sided fern rosette with folded pinnae, in metres."""

import math
import sys
from pathlib import Path
from random import Random

from bind_pilgrim import Output, cross, unit


def bake(out):
    g = Output()
    g.doc.update(nodes=[{"mesh": 0}], meshes=[], scenes=[{"nodes": [0]}])
    g.doc["asset"]["generator"] = "Vesper valley ferns"
    # Dusk greens, varied between old leaves and the new yellow-green growth.
    tones = [
        (0.058, 0.105, 0.036),
        (0.088, 0.154, 0.048),
        (0.135, 0.185, 0.057),
        (0.10, 0.117, 0.040),
    ]
    g.doc["materials"] = [
        {
            "name": "FernTone" + str(i),
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorFactor": [*c, 1],
                "metallicFactor": 0,
                "roughnessFactor": 0.79,
            },
        }
        for i, c in enumerate(tones)
    ]
    positions = [[] for _ in tones]
    normals = [[] for _ in tones]

    def tri(idx, a, b, c):
        n = unit(
            cross(
                tuple(x - y for x, y in zip(b, a)), tuple(x - y for x, y in zip(c, a))
            )
        )
        if n[1] < 0:
            b, c = c, b
            n = tuple(-v for v in n)
        positions[idx].extend([a, b, c])
        normals[idx].extend([n] * 3)

    rng = Random(7391)

    def frond(j):
        theta = j * 2.399 + rng.uniform(-0.18, 0.18)
        d = (math.cos(theta), math.sin(theta))
        side = (-d[1], d[0])
        spread = rng.uniform(0.26, 0.73)
        rise = rng.uniform(0.24, 0.52)

        def pt(t, w=0, dy=0):
            radius = spread * (0.08 * t + 0.92 * t**1.45)
            return (
                d[0] * radius + side[0] * w,
                rise * (1.42 * t - 0.77 * t * t) + 0.097 * math.sin(t * math.pi) + dy,
                d[1] * radius + side[1] * w,
            )

        for k in range(14):
            t = k / 14
            u = (k + 1) / 14
            a, b, c, e = pt(t, -0.003), pt(t, 0.003), pt(u, 0.003), pt(u, -0.003)
            tri(2, a, b, c)
            tri(2, a, c, e)

        def pin(t, sign, length, u, edge=0):
            along = t + 0.115 * u + edge * 0.025 * math.sin(math.pi * u)
            width = sign * (length * u)
            return pt(
                along,
                width,
                0.033 * math.sin(u * math.pi) + 0.006 * (1 - abs(edge)) - 0.031 * u * u,
            )

        for k in range(12):
            t = 0.14 + k * 0.071
            length = spread * (0.095 + 0.15 * math.sin(math.pi * t)) * (1 - 0.62 * t)
            for sign in (-1, 1):
                color = rng.choices(range(4), weights=[0.28, 0.44, 0.20, 0.08])[0]

                for n in range(5):
                    a = n / 5
                    b = (n + 1) / 5
                    for edge in (-1, 1):
                        # Saw-tooth margins. Each pair folds up at its central rib.
                        start = pin(t, sign, length, a)
                        end = pin(t, sign, length, b)
                        middle = pin(t, sign, length, a + 0.085, edge * (1 - 0.11 * n))
                        tri(color, start, middle, end)

    for j in range(19):
        frond(j)
    primitives = []
    for idx, (p, n) in enumerate(zip(positions, normals)):
        primitives.append(
            {
                "attributes": {
                    "POSITION": g.data(p, "VEC3", bounds=True),
                    "NORMAL": g.data(n, "VEC3"),
                },
                "material": idx,
            }
        )
    g.doc["meshes"].append({"name": "ValleyFern", "primitives": primitives})
    g.save(out)


if __name__ == "__main__":
    bake(Path(sys.argv[1]))
