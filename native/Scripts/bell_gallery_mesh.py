"""Bake the open timber shelter at the bell court. Coordinates are glTF metres."""

from collections import defaultdict
from math import cos, dist, pi, sin, tau

from bind_pilgrim import Output, cross, unit


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def scale(v, amount):
    return tuple(x * amount for x in v)


class Joinery:
    def __init__(self, source):
        self.source = source
        self.glb = Output()
        self.glb.doc["asset"]["generator"] = "Vesper bell court rain gallery"
        self.glb.doc["meshes"] = [{"name": "BellRainGallery", "primitives": []}]
        self.glb.doc["nodes"] = [{"name": "BellRainGallery", "mesh": 0}]
        self.images = {}
        self.sections = defaultdict(lambda: ([], [], [], []))

    def image(self, file):
        if file not in self.images:
            self.images[file] = self.glb.image(
                (self.source / (file + ".jpg")).read_bytes(), "image/jpeg", file
            )
        return self.images[file]

    def material(self, name, diffuse, normal, tint, rough, metal=0):
        pbr = dict(
            baseColorFactor=[*tint, 1], roughnessFactor=rough, metallicFactor=metal
        )
        if diffuse:
            pbr["baseColorTexture"] = self.image(diffuse)
        mat = dict(name=name, pbrMetallicRoughness=pbr, doubleSided=True)
        if normal:
            mat["normalTexture"] = dict(self.image(normal), scale=0.63)
        index = len(self.glb.doc["materials"])
        self.glb.doc["materials"].append(mat)
        return index

    def face(self, mat, points, outward, uv=None):
        p, n, t, indices = self.sections[mat]
        edge = lambda i: tuple(a - b for a, b in zip(points[i], points[0]))
        norm = unit(cross(edge(1), edge(2)))
        if not any(norm):
            return
        if uv is None:
            length, height = dist(points[0], points[1]), dist(points[0], points[-1])
            uv = [(0, 0), (length, 0), (length, height), (0, height)][: len(points)]
        if sum(a * b for a, b in zip(norm, outward)) < 0:
            points, uv = points[::-1], uv[::-1]
            norm = scale(norm, -1)
        i = len(p)
        p.extend(points)
        n.extend([norm] * len(points))
        t.extend(uv)
        for j in range(1, len(points) - 1):
            indices.extend([i, i + j, i + j + 1])

    def beam(self, mat, a, b, width, depth):
        axis = unit(tuple(y - x for x, y in zip(a, b)))
        guide = (0, 1, 0) if abs(axis[1]) < 0.95 else (1, 0, 0)
        side = scale(unit(cross(axis, guide)), width / 2)
        up = scale(unit(cross(side, axis)), depth / 2)
        corners = [
            add(scale(side, s), scale(up, u))
            for s, u in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        lower, upper = [[add(origin, v) for v in corners] for origin in (a, b)]
        for j in range(4):
            k = (j + 1) % 4
            self.face(
                mat,
                [lower[j], upper[j], upper[k], lower[k]],
                add(corners[j], corners[k]),
            )
        self.face(mat, lower, scale(axis, -1))
        self.face(mat, upper, axis)

    def turned(self, mat, x, z, rings, sides=14):
        for (h, r), (hh, rr) in zip(rings, rings[1:]):
            for i in range(sides):
                a, b = tau * i / sides, tau * (i + 1) / sides
                pts = [
                    (x + rad * cos(ang), y, z + rad * sin(ang))
                    for y, rad, ang in ((h, r, a), (h, r, b), (hh, rr, b), (hh, rr, a))
                ]
                self.face(
                    mat,
                    pts,
                    (cos((a + b) / 2), 0, sin((a + b) / 2)),
                    [
                        (i / sides, h),
                        ((i + 1) / sides, h),
                        ((i + 1) / sides, hh),
                        (i / sides, hh),
                    ],
                )

    def save(self, dest):
        for mat, (pos, nor, uv, indices) in self.sections.items():
            attrs = dict(
                POSITION=self.glb.data(pos, "VEC3", bounds=True),
                NORMAL=self.glb.data(nor, "VEC3"),
                TEXCOORD_0=self.glb.data(uv, "VEC2"),
            )
            self.glb.doc["meshes"][0]["primitives"].append(
                dict(
                    attributes=attrs,
                    indices=self.glb.data([(i,) for i in indices], "SCALAR", 5125),
                    material=mat,
                )
            )
        self.glb.save(dest)


def bake(source, destination):
    g = Joinery(source)
    cedar = g.material(
        "OldCedar", "wood-color", "wood-normal", (0.42, 0.33, 0.27), 0.64
    )
    red = g.material(
        "OxideLacquer", "wood-color", "wood-normal", (0.75, 0.23, 0.16), 0.49
    )
    stone = g.material(
        "GraniteFoot", "rock-color", "rock-normal", (0.72, 0.76, 0.73), 0.84
    )
    tile = g.material("KilnGrey", "rock-color", "rock-normal", (0.30, 0.40, 0.42), 0.56)
    rim = g.material("GlazedRim", "rock-color", "rock-normal", (0.43, 0.53, 0.50), 0.40)
    gilt = g.material(
        "OldBronze", "metal-color", "metal-normal", (0.69, 0.43, 0.20), 0.48, 0.61
    )
    paint = g.material(
        "PaintedFascia", "belfry-dragon-beam", None, (0.78, 0.73, 0.69), 0.64
    )
    paper = g.material("SilkLantern", "belfry-paper", None, (1, 0.71, 0.41), 0.76)
    silk = g.glb.doc["materials"][paper]
    silk["emissiveTexture"] = g.image("belfry-paper")
    silk["emissiveFactor"] = [0.85, 0.40, 0.12]
    # Four column pairs. The 10.5 m clear nave carries the duel and dodge lane.
    stations = (-6.60, -2.20, 2.20, 6.60)
    for side in (-1, 1):
        z = 5.45 * side
        for x in stations:
            g.turned(
                stone,
                x,
                z,
                [
                    (0, 0.42),
                    (0.09, 0.42),
                    (0.13, 0.34),
                    (0.18, 0.38),
                    (0.27, 0.33),
                    (0.31, 0.27),
                ],
            )
            g.turned(
                red,
                x,
                z,
                [(0.29, 0.255), (0.45, 0.235), (3.65, 0.205), (3.90, 0.22)],
                24,
            )
            for h in (0.41, 3.69):
                g.turned(
                    gilt,
                    x,
                    z,
                    [
                        (h, 0.241 if h < 1 else 0.218),
                        (h + 0.032, 0.241 if h < 1 else 0.218),
                    ],
                )
            # Interleaved arms and bearing blocks step the load out to the eaves.
            for k in range(3):
                h = 3.79 + 0.18 * k
                arm = 0.38 + 0.22 * k
                if k % 2:
                    a, b = (x - arm, h, z), (x + arm, h, z)
                else:
                    a, b = (x, h, z - arm), (x, h, z + arm)
                g.beam(cedar, a, b, 0.22, 0.17)
                for p in (a, b):
                    g.beam(
                        red, (p[0], h + 0.08, p[2]), (p[0], h + 0.21, p[2]), 0.26, 0.23
                    )
            for direction in (-1, 1):
                g.beam(red, (x, 3.37, z), (x + direction * 0.69, 3.95, z), 0.15, 0.14)
        for h, depth, mat in (
            (3.91, 0.26, cedar),
            (4.20, 0.24, red),
            (4.42, 0.22, cedar),
        ):
            g.beam(mat, (-7.25, h, z), (7.25, h, z), 0.32, depth)
        for bay, (lo, hi) in enumerate(zip(stations, stations[1:])):
            # Narrow painted spandrels remain above the open sightline.
            face_z = z - side * 0.167
            g.face(
                paint,
                [
                    (lo + 0.26, 4.32, face_z),
                    (hi - 0.26, 4.32, face_z),
                    (hi - 0.26, 4.09, face_z),
                    (lo + 0.26, 4.09, face_z),
                ],
                (0, 0, -side),
                [(0, 0), (1, 0), (1, 1), (0, 1)],
            )
            if side == 1:
                continue
            # Two backed bays and one open bay let light rake across the floor.
            if bay == 1:
                continue
            for h, width in ((0.23, 0.40), (0.57, 0.33), (0.86, 0.42)):
                g.beam(stone, (lo + 0.18, h, z), (hi - 0.18, h, z), width, 0.32)
            for h in (1.0, 3.43):
                g.beam(cedar, (lo + 0.19, h, z), (hi - 0.19, h, z), 0.14, 0.14)
            for panel in range(4):
                mid = lo + 0.70 + panel
                for dx in (-0.46, 0.46):
                    g.beam(
                        cedar, (mid + dx, 1.03, z), (mid + dx, 3.43, z), 0.085, 0.085
                    )
                for h in (1.36, 2.02, 2.70, 3.15):
                    g.beam(red, (mid - 0.46, h, z), (mid + 0.46, h, z), 0.055, 0.055)
                for h in (1.69, 2.36):
                    corners = [
                        (mid - 0.40, h, z),
                        (mid, h + 0.29, z),
                        (mid + 0.40, h, z),
                        (mid, h - 0.29, z),
                    ]
                    for a, b in zip(corners, corners[1:] + corners[:1]):
                        g.beam(cedar, a, b, 0.048, 0.055)

    for x in stations:
        g.beam(cedar, (x, 4.37, -5.66), (x, 4.37, 5.66), 0.34, 0.30)
        for side in (-1, 1):
            g.beam(red, (x, 3.62, side * 5.40), (x, 4.32, side * 4.40), 0.15, 0.17)
            g.beam(cedar, (x, 4.50, side * 4.80), (x, 6.44, side * 0.35), 0.21, 0.22)
        g.beam(cedar, (x, 4.50, 0), (x, 6.70, 0), 0.23, 0.26)
    g.beam(cedar, (-6.86, 6.64, 0), (6.86, 6.64, 0), 0.32, 0.28)

    def roof(end, side, u, v):
        y = 4.65 + 2.28 * v**1.48 + 0.43 * abs(u) ** 5 * (1 - v) ** 2
        if end:
            return (side * (8.10 - 2.42 * v), y, u * 6.82 * (1 - v))
        return (u * (8.10 - 2.42 * v), y, side * 6.82 * (1 - v))

    for end in (False, True):
        for side in (-1, 1):

            def pt(u, v, dy=0):
                return add(roof(end, side, u, v), (0, dy, 0))

            outward = (side, 0, 0) if end else (0, 0, side)
            n = 38 if end else 76
            # Closed soffit plus a continuous tile bed; raised rolls catch the low sun.
            for i in range(n):
                u, b = -1 + 2 * i / n, -1 + 2 * (i + 1) / n
                for k in range(8):
                    v, w = k / 8, (k + 1) / 8
                    for mat, dy, up in ((tile, 0, 1), (cedar, -0.16, -1)):
                        corners = [
                            pt(u, v, dy),
                            pt(b, v, dy),
                            pt(b, w, dy),
                            pt(u, w, dy),
                        ]
                        if end and k == 7:
                            corners = corners[:3]
                        g.face(mat, corners, (0, up, 0))
                    if not end or k < 6:
                        for j in range(5):
                            lo, hi = pi * j / 5, pi * (j + 1) / 5

                            def roll(angle, t):
                                return pt(
                                    u + 0.0062 * (1 - cos(angle)),
                                    t,
                                    0.008 + 0.067 * sin(angle),
                                )

                            g.face(
                                rim,
                                [roll(lo, v), roll(hi, v), roll(hi, w), roll(lo, w)],
                                (0, 1, 0),
                            )
                    if i % 5 == 0 and (not end or k < 5):
                        g.beam(cedar, pt(u, v, -0.19), pt(u, w, -0.19), 0.082, 0.095)
                g.face(
                    red, [pt(u, 0, -0.16), pt(b, 0, -0.16), pt(b, 0), pt(u, 0)], outward
                )
            # Capped sloping hips carry a second thin line above the tile bed.
            if not end:
                for tip in (-1, 1):
                    for k in range(10):
                        a, b = pt(tip, k / 10, 0.07), pt(tip, (k + 1) / 10, 0.07)
                        g.beam(rim, a, b, 0.20, 0.14)
    g.beam(tile, (-5.8, 7.03, 0), (5.8, 7.03, 0), 0.35, 0.24)
    g.beam(rim, (-5.93, 7.17, 0), (5.93, 7.17, 0), 0.22, 0.10)
    for s in (-1, 1):
        for i in range(5):
            g.beam(
                rim,
                (s * (5.68 + 0.10 * i), 7.08 + 0.022 * i * i, 0),
                (s * (5.78 + 0.10 * i), 7.10 + 0.022 * (i + 1) ** 2, 0),
                0.16,
                0.15,
            )
    # Lacquered octagonal hanging lanterns. The paper and its ribs are independent.
    for x, z in ((-4.38, -4.82), (4.38, -4.82)):
        g.turned(gilt, x, z, [(3.62, 0.018), (4.38, 0.018)], 8)
        for i in range(8):
            a, b = tau * i / 8, tau * (i + 1) / 8

            def corner(t, h, r):
                return (x + r * cos(t), h, z + r * sin(t))

            g.face(
                paper,
                [
                    corner(a, 2.92, 0.30),
                    corner(b, 2.92, 0.30),
                    corner(b, 3.48, 0.30),
                    corner(a, 3.48, 0.30),
                ],
                (cos((a + b) / 2), 0, sin((a + b) / 2)),
                [(0, 1), (1, 1), (1, 0), (0, 0)],
            )
            g.beam(red, corner(a, 2.90, 0.30), corner(a, 3.50, 0.30), 0.027, 0.027)
        for h in (2.90, 3.50):
            g.turned(
                gilt,
                x,
                z,
                [
                    (h - 0.055, 0.19),
                    (h - 0.028, 0.34),
                    (h + 0.03, 0.34),
                    (h + 0.07, 0.19),
                ],
                8,
            )
        g.turned(red, x, z, [(2.56, 0.026), (2.77, 0.052), (2.84, 0.02)], 10)
    g.save(destination)
