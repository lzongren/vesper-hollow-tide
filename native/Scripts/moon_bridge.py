"""Build the three-arched garden bridge and the embankments of its lotus pond.
Local glTF coordinates are metres, with Y up and the span along Z.
"""

from math import cos, sin, pi, floor
from random import Random
from bell_gallery_mesh import Joinery

WATER = -0.94


def deck(z):
    # Level treads cut in 13 cm increments. Approaches start at the quay level.
    t = max(0, min(1, (13.90 - abs(z)) / 11.85))
    return 0.10 + 0.13 * floor(30 * (1 - (1 - t) ** 1.48) + 0.0001)


def bridge(source, dest):
    g = Joinery(source)
    g.glb.doc["meshes"][0]["name"] = "LotusBridge"
    g.glb.doc["nodes"][0]["name"] = "LotusBridge"
    g.glb.doc["asset"]["generator"] = "Vesper crescent bridge and lotus quay"

    def stone(name, tint, rough=0.85):
        return g.material(name, "rock-color", "rock-normal", tint, rough)

    ash = stone("PaleWeatheredStone", (0.56, 0.63, 0.61))
    ribs = stone("CloudGreyArch", (0.69, 0.70, 0.64), 0.72)
    dark = stone("BasaltSpringer", (0.19, 0.28, 0.27), 0.78)
    block = g.material(
        "SawnQuay", "stone-color", "stone-normal", (0.55, 0.58, 0.52), 0.77
    )
    curb = stone("PittedKerb", (0.39, 0.45, 0.40))
    silt = stone("ShallowBed", (0.21, 0.28, 0.20), 0.94)

    def box(mat, x, y, z, wx, hy, wz):
        g.beam(mat, (x - wx / 2, y, z), (x + wx / 2, y, z), wz, hy)

    def elevation(z):
        # Intrados: three segmental vaults spring from the same waterline.
        for mid, rad, rise in (
            (-8.78, 2.44, 1.49),
            (0, 5.14, 3.28),
            (8.78, 2.44, 1.49),
        ):
            a = (z - mid) / rad
            if abs(a) < 1:
                return -0.66 + rise * (max(0, 1 - a * a) ** 0.5)
        return -2.58

    # Vertical polygons form the spandrels; transverse faces describe the
    # whole underside of the vault, so its reflection has a real inner surface.
    cuts = {-14.0, 14.0}
    for mid, r, hi in ((-8.78, 2.44, 1.49), (0, 5.14, 3.28), (8.78, 2.44, 1.49)):
        cuts.update(mid + r * cos(pi * j / 40) for j in range(41))
    for j in range(121):
        cuts.add(-14 + 28 * j / 120)
    zs = sorted(cuts)
    width = 1.69
    for a, b in zip(zs, zs[1:]):
        za, zb = elevation(a), elevation(b)
        h = deck((a + b) / 2) - 0.075
        for side in (-1, 1):
            x = side * width
            g.face(
                ash,
                [(x, za, a), (x, zb, b), (x, h, b), (x, h, a)],
                (side, 0, 0),
                [(a / 2, za / 2), (b / 2, zb / 2), (b / 2, h / 2), (a / 2, h / 2)],
            )
        g.face(
            dark,
            [(-width, za, a), (width, za, a), (width, zb, b), (-width, zb, b)],
            (0, -1, 0),
        )
        g.face(
            block,
            [(-width, h, a), (-width, h, b), (width, h, b), (width, h, a)],
            (0, 1, 0),
        )
    for mid, r, rise, n in (
        (-8.78, 2.44, 1.49, 17),
        (0, 5.14, 3.28, 29),
        (8.78, 2.44, 1.49, 17),
    ):
        for i in range(n):
            a, b = pi * (i + 0.032) / n, pi * (i + 0.968) / n
            for side in (-1, 1):
                extra = 0.15 if i == n // 2 else 0
                # Individually cut stones project beyond the spandrel, with
                # a raised crown keystone and a second narrow outer archivolt.
                for inside, outside, offset, mat in (
                    (0, 0.43 + extra, 0.13 + extra * 0.28, ribs),
                    (0.48 + extra, 0.57 + extra, 0.072, curb),
                ):

                    def profile(t, d):
                        return (-0.66 + (rise + d) * sin(t), mid + (r + d) * cos(t))

                    front = [
                        (side * (width + offset), *profile(t, d))
                        for t, d in (
                            (a, inside),
                            (b, inside),
                            (b, outside),
                            (a, outside),
                        )
                    ]
                    g.face(mat, front, (side, 0, 0))
                    for j in range(4):
                        u, v = front[j], front[(j + 1) % 4]
                        g.face(
                            mat,
                            [u, v, (side * width, *v[1:]), (side * width, *u[1:])],
                            (0, -sin((a + b) / 2) if j == 0 else 1, cos(a)),
                        )
    # Breakwaters at the two central piers carry the springing loads.
    for z in (-6.03, 6.03):
        for s in (-1, 1):
            for y, extent, w in (
                (-1.79, 1.84, 1.83),
                (-0.86, 1.58, 1.53),
                (-0.20, 1.34, 1.25),
                (0.12, 1.45, 1.30),
            ):
                tri = [
                    (s * 1.55, y, z - w / 2),
                    (s * (1.60 + extent), y, z),
                    (s * 1.55, y, z + w / 2),
                ]
                g.face(ribs, tri, (0, 1, 0))
                for j in (0, 1):
                    u, v = tri[j], tri[j + 1]
                    g.face(
                        dark,
                        [u, v, (v[0], y - 0.88, v[2]), (u[0], y - 0.88, u[2])],
                        (s, 0, 0),
                    )
    # Separate transverse flags preserve the rise and the comb of tread shadows.
    for i in range(96):
        z = -14 + (i + 0.5) * 28 / 96
        box(block, 0, deck(z) - 0.053, z, 3.56, 0.132, 28 / 96 - 0.006)
    for side in (-1, 1):
        x = side * 1.68
        for i in range(19):
            z = -13.68 + i * 1.52
            h = deck(z)
            g.turned(
                ribs,
                x,
                z,
                [
                    (h - 0.10, 0.23),
                    (h + 0.08, 0.24),
                    (h + 0.15, 0.18),
                    (h + 0.78, 0.15),
                    (h + 0.82, 0.21),
                    (h + 0.90, 0.21),
                    (h + 0.96, 0.14),
                    (h + 1.06, 0.17),
                    (h + 1.15, 0.11),
                    (h + 1.18, 0.04),
                ],
                8,
            )
            if i == 18:
                continue
            z1 = z + 1.52
            for lift, w, d, m in ((0.83, 0.145, 0.14, ribs), (0.30, 0.100, 0.14, curb)):
                g.beam(
                    m, (x, h + lift, z + 0.13), (x, deck(z1) + lift, z1 - 0.13), w, d
                )
            # A pierced lozenge inside each bay keeps sky visible above the span.
            m = (z + z1) / 2
            hh = (h + deck(z1)) / 2 + 0.54
            for a, b in (
                ((z + 0.24, h + 0.53), (m, hh + 0.20)),
                ((m, hh + 0.20), (z1 - 0.24, deck(z1) + 0.53)),
                ((z + 0.24, h + 0.53), (m, hh - 0.20)),
                ((m, hh - 0.20), (z1 - 0.24, deck(z1) + 0.53)),
            ):
                g.beam(curb, (x, a[1], a[0]), (x, b[1], b[0]), 0.086, 0.08)
    # Rectangular stone quay; only its back and side retaining walls meet water.
    for edge in (-1, 1):
        for i in range(20):
            x = -11.9 + (i + 0.5) * 1.27
            box(dark, x, -1.36, edge * 14, 1.27, 2.86, 1.53)
            box(block, x, 0.035, edge * 14, 1.265, 0.155, 1.69)
        for i in range(22):
            z = -14 + (i + 0.5) * 28 / 22
            x = -11.9 if edge < 0 else 13.50
            box(dark, x, -1.35, z, 1.11, 2.80, 28 / 22)
            box(block, x, 0.035, z, 1.34, 0.155, 28 / 22 - 0.009)
    # Two bands of stratified silt remain visible beneath the near shore.
    box(silt, 0.75, -2.55, 0, 25.5, 0.14, 28.5)
    rng = Random(781)
    for i in range(38):
        z = rng.uniform(-12.7, 12.7)
        x = rng.choice((-1, 1)) * rng.uniform(8.2, 10.8)
        y = rng.uniform(-1.79, -1.04)
        r = rng.uniform(0.16, 0.51)
        g.turned(
            curb,
            x,
            z,
            [(y - 0.22, r * 0.65), (y, r), (y + 0.14, r * 0.74), (y + 0.19, r * 0.28)],
            7,
        )
    g.save(dest)
