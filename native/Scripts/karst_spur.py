"""Build the fluted limestone flanks and broken crowns of the mountain spurs."""

import math
from random import Random

from bind_pilgrim import Output, cross, unit


def bake(path, seed):
    rng = Random(seed)
    phases = [rng.uniform(0, 2 * math.pi) for _ in range(9)]
    pos, uv, tint, indices = [], [], [], []
    # Overlapping buttresses have a common geological strike but individual crests.
    formations = [
        (-32, 0, 27, 18, 36),
        (-12, -2, 26, 18, 52),
        (9, 2, 23, 19, 63),
        (29, 1, 22, 14, 47),
        (44, 4, 17, 12, 32),
        (-18, 12, 17, 12, 27),
        (12, 14, 14, 11, 31),
    ]
    for cx, cz, radius_x, radius_z, height in formations:
        phase = rng.uniform(-2, 2)
        height *= rng.uniform(0.78, 1.17)
        radius_z *= rng.uniform(0.85, 1.12)
        segments, courses = 92, 49
        for row in range(courses + 1):
            t = row / courses
            # Three distinct slope regimes: foot talus, a steep face and a cap.
            radius = (1 - t) ** 0.28 * (0.64 + 0.36 * math.exp(-6 * t))
            for col in range(segments + 1):
                a = math.tau * (col % segments) / segments
                fold = (
                    math.cos(5 * a + phases[0])
                    + 0.61 * math.cos(9 * a + phase + 0.7 * t)
                    + 0.39 * math.cos(17 * a + phases[2] - t)
                )
                cleft = max(0, math.cos(8 * a + phase - 0.7 * t)) ** 8
                bedding = 0.023 * math.tanh(
                    3.8 * math.sin(36 * t + 1.9 * math.sin(a + 0.3) + phase)
                )
                r = radius * (1 + 0.105 * fold - 0.18 * cleft + bedding)
                x = cx + r * radius_x * math.cos(a) + t * 3.2
                z = cz + r * radius_z * math.sin(a) + t * 1.9
                peak = (
                    0.88
                    + 0.12 * math.cos(2 * a + phase)
                    + 0.055 * math.sin(6 * a + phases[5])
                )
                # Converge to one shared summit above the fractured shoulders.
                y = -4 + height * t * (peak * (1 - t**8) + t**8)
                pos.append((x, y, z))
                uv.append(
                    (col / segments * (radius_x + radius_z) * math.pi / 4.2, -y / 4.2)
                )
                shelf = min(
                    1,
                    max(
                        0,
                        0.63 - 0.9 * math.sin(36 * t + 1.9 * math.sin(a + 0.3) + phase),
                    ),
                )
                moss = min(
                    1, 0.38 * shelf + 0.36 * cleft + 0.32 * (1 - t) ** 4 + 0.48 * t**7
                )
                shade = 0.85 + 0.10 * math.cos(3 * a + phase) - 0.12 * cleft
                tint.append(
                    (
                        (0.68 - 0.44 * moss) * shade,
                        (0.70 - 0.30 * moss) * shade,
                        (0.69 - 0.44 * moss) * shade,
                        1,
                    )
                )
                if row and col:
                    k = len(pos) - 1
                    a0, b, c, d = k - segments - 2, k - segments - 1, k, k - 1
                    indices.extend((a0, d, b, b, d, c))
    # Normals accumulate across each welded longitude seam and summit.
    normals = [[0.0, 0.0, 0.0] for _ in pos]
    for j in range(0, len(indices), 3):
        i, k, m = indices[j : j + 3]
        n = cross(
            [b - a for a, b in zip(pos[i], pos[k])],
            [b - a for a, b in zip(pos[i], pos[m])],
        )
        for ix in (i, k, m):
            for c in range(3):
                normals[ix][c] += n[c]
    for first in range(0, len(pos), (courses + 1) * (segments + 1)):
        for row in range(courses + 1):
            i = first + row * (segments + 1)
            seam = [a + b for a, b in zip(normals[i], normals[i + segments])]
            normals[i] = normals[i + segments] = seam
        top = first + courses * (segments + 1)
        normals[top : top + segments + 1] = [[0, 1, 0]] * (segments + 1)
    out = Output()
    out.doc["asset"]["generator"] = "Vesper limestone spur"
    out.doc["nodes"] = [dict(mesh=0, name=path.stem)]
    out.doc["meshes"][0]["name"] = path.stem
    out.doc["materials"] = [
        dict(
            name="BeddedLimestone",
            pbrMetallicRoughness=dict(metallicFactor=0, roughnessFactor=0.91),
        )
    ]
    attrs = dict(
        POSITION=out.data(pos, "VEC3", bounds=True),
        NORMAL=out.data([unit(n) for n in normals], "VEC3"),
        COLOR_0=out.data(tint, "VEC4"),
        TEXCOORD_0=out.data(uv, "VEC2"),
    )
    out.doc["meshes"][0]["primitives"] = [
        dict(
            attributes=attrs,
            indices=out.data([(i,) for i in indices], "SCALAR", 5125),
            material=0,
        )
    ]
    out.save(path)
