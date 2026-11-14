"""Bake the inscribed bronze seal at unit radius in glTF metres."""

from math import cos, sin, pi, tau
from bind_pilgrim import Output, cross, unit


def bake(path):
    out = Output()
    name = "PrayerSeal"
    out.doc["nodes"] = [dict(mesh=0, name=name)]
    out.doc["meshes"][0]["name"] = name
    out.doc["materials"].append(
        dict(
            name="BankedEmber",
            pbrMetallicRoughness=dict(baseColorFactor=[1, 0.22, 0.025, 1]),
            doubleSided=True,
        )
    )
    p = []
    n = []
    idx = []

    def tri(a, b, c):
        normal = unit(
            cross(
                tuple(i - j for i, j in zip(b, a)), tuple(i - j for i, j in zip(c, a))
            )
        )
        idx.extend(range(len(p), len(p) + 3))
        p.extend((a, b, c))
        n.extend([normal] * 3)

    def polar(r, angle, h):
        return (r * cos(angle), h, r * sin(angle))

    def band(rad, width, a, b, steps, height):
        for i in range(steps):
            t = a + (b - a) * i / steps
            s = a + (b - a) * (i + 1) / steps
            A, B, C, D = (
                polar(rad, t, height),
                polar(rad, s, height),
                polar(rad - width, s, height),
                polar(rad - width, t, height),
            )
            tri(A, C, B)
            tri(A, D, C)

    band(1, 0.032, 0, tau, 144, 0.025)
    band(0.86, 0.018, 0, tau, 144, 0.028)
    for j in range(36):
        a = j * tau / 36
        band(0.966, 0.087 if j % 3 else 0.13, a, a + 0.028, 2, 0.032)
        if j % 3 == 0:
            for k in range(12):
                t = k / 12
                s = (k + 1) / 12

                def petal(v, side):
                    return polar(
                        0.83 - 0.21 * sin(pi * v),
                        a + side * 0.107 * sin(pi * v) + 0.038 * (v - 0.5),
                        0.03,
                    )

                tri(petal(t, 1), petal(s, 1), petal(s, -1))
                tri(petal(t, 1), petal(s, -1), petal(t, -1))
    attrs = dict(POSITION=out.data(p, "VEC3", bounds=True), NORMAL=out.data(n, "VEC3"))
    out.doc["meshes"][0]["primitives"] = [
        dict(
            attributes=attrs,
            indices=out.data([(i,) for i in idx], "SCALAR", 5125),
            material=0,
        )
    ]
    out.save(path)
