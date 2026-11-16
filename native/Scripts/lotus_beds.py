"""Water lilies and lotus in small colonies along the sheltered stone banks."""

from math import cos, sin, pi, tau
from random import Random
from bell_gallery_mesh import Joinery
from bind_pilgrim import cross, unit
from moon_bridge import WATER


def pond_mesh(source, name):
    art = Joinery(source)
    art.glb.doc["asset"]["generator"] = "Vesper moon court garden"
    for group in ("meshes", "nodes"):
        art.glb.doc[group][0]["name"] = name
    return art


def surface(source, dest):
    art = pond_mesh(source, "LotusWater")
    mat = art.material("PondSurface", None, None, (0.034, 0.10, 0.075), 0.18)
    art.face(
        mat,
        [
            (-11.90, WATER, -14),
            (-11.90, WATER, 14),
            (13.50, WATER, 14),
            (13.50, WATER, -14),
        ],
        (0, 1, 0),
        [(0, 0), (0, 28), (25.4, 28), (25.4, 0)],
    )
    art.save(dest)


def curved_surface(art, slot, around, along, point, texture):
    """Share vertices and differentiate the parametric leaf or petal for smooth shading."""
    pts, normals, uv, indices = art.sections[slot]
    start = len(pts)
    for j in range(along + 1):
        for i in range(around + 1):
            u, v = i / around, j / along
            mid = max(0.002, min(0.998, v))
            a, b = point(min(1, u + 0.001), mid), point(max(0, u - 0.001), mid)
            c, d = point(u, mid + 0.001), point(u, mid - 0.001)
            normals.append(
                unit(
                    cross(
                        tuple(x - y for x, y in zip(a, b)),
                        tuple(x - y for x, y in zip(c, d)),
                    )
                )
            )
            pts.append(point(u, v))
            uv.append(texture(u, v))
            if j and i:
                k = start + j * (around + 1) + i
                indices.extend(
                    (k - around - 2, k - around - 1, k, k - around - 2, k, k - 1)
                )


def planting(source, dest):
    art = pond_mesh(source, "GardenLotus")
    rng = Random(1713)
    leaf_texture = art.glb.image(
        (source.parent / "Art/MoonGarden/lotus-leaf.jpg").read_bytes(),
        "image/jpeg",
        "LotusLeaf",
    )
    jade = []
    for i, tint in enumerate(
        ((0.65, 0.88, 0.81), (0.79, 0.97, 0.82), (0.58, 0.85, 0.85), (0.92, 0.93, 0.72))
    ):
        slot = art.material("LotusLeaf" + str(i), None, None, tint, 0.55)
        art.glb.doc["materials"][slot]["pbrMetallicRoughness"]["baseColorTexture"] = (
            leaf_texture
        )
        jade.append(slot)
    stalk = art.material("PondStems", None, None, (0.074, 0.142, 0.057), 0.71)
    petal = art.material("LotusIvory", None, None, (0.97, 0.97, 0.95), 0.49)
    petal_tex = art.glb.image(
        (source.parent / "Art/MoonGarden/lotus-petal.jpg").read_bytes(),
        "image/jpeg",
        "PetalVeins",
    )
    art.glb.doc["materials"][petal]["pbrMetallicRoughness"]["baseColorTexture"] = (
        petal_tex
    )
    seed = art.material("LotusReceptacle", None, None, (0.51, 0.31, 0.078), 0.63)

    def leaf(x, z, r, h, tilt):
        turn = rng.random() * tau
        roll = rng.uniform(0.04, 0.14)

        def point(t, d):
            a = turn + t
            span = r * d * (1 + 0.045 * sin(5 * t) + 0.035 * sin(8 * t + 0.5))
            return (
                x + span * cos(a),
                h
                + tilt * d * cos(t - 0.3)
                + r * d * d * (roll + 0.032 * cos(7 * t) + 0.065 * sin(3 * t + 0.8)),
                z + span * sin(a),
            )

        slot = rng.choice(jade)

        def tex(t, d):
            return (0.5 + 0.487 * d * cos(t), 0.5 + 0.487 * d * sin(t))

        curved_surface(
            art,
            slot,
            54,
            7,
            lambda u, v: point(0.012 + 6.259 * u, v),
            lambda u, v: tex(0.012 + 6.259 * u, v),
        )
        art.beam(
            stalk, (x + 0.026, WATER - 0.32, z - 0.042), (x, h + 0.013, z), 0.014, 0.014
        )

    def flower(x, z, h, k):
        art.beam(stalk, (x - 0.05, WATER - 0.34, z + 0.08), (x, h, z), 0.023, 0.023)
        for row, n in enumerate((8, 7, 6)):
            for j in range(n):
                angle = tau * (j / n + 0.077 * row) + 0.09 * sin(j * 5.1 + x)
                length = k * (0.27 - 0.037 * row) * (1 + 0.10 * cos(3 * j + z))
                pitch = 0.38 + 0.18 * row + 0.09 * sin(x + 3 * j)

                def blade(u, v):
                    side = 2 * u - 1
                    span = length * 0.33 * (0.022 + sin(pi * v) ** 0.83) * side
                    reach = (
                        0.018 * k
                        + length * (1 - 0.19 * row) * v
                        + 0.012 * k * sin(pi * v)
                    )
                    rise = length * (
                        0.02
                        + pitch * v
                        + 0.25 * sin(pi * v)
                        + 0.16 * side**2 * sin(pi * v)
                    )
                    rise -= 0.047 * k * (1 - 0.28 * row) * v**4
                    bend = 0.014 * k * sin(j + 0.5 * row) * sin(pi * v)
                    return (
                        x + reach * cos(angle) - (span + bend) * sin(angle),
                        h + rise,
                        z + reach * sin(angle) + (span + bend) * cos(angle),
                    )

                curved_surface(
                    art,
                    petal,
                    8,
                    14,
                    blade,
                    lambda u, v: (0.08 + 0.84 * u, 1 - 0.96 * v),
                )
        # Anthers sit just outside the raised receptacle, inside the innermost petals.
        for j in range(21):
            angle = j * tau / 21
            rx = x + 0.046 * k * cos(angle)
            rz = z + 0.046 * k * sin(angle)
            height = h + k * (0.117 + 0.011 * sin(3 * j))
            art.turned(
                seed,
                rx,
                rz,
                [
                    (h + 0.079 * k, 0.0018 * k),
                    (height, 0.0026 * k),
                    (height + 0.005 * k, 0.0049 * k),
                    (height + 0.009 * k, 0.0029 * k),
                ],
                6,
            )
        art.turned(
            seed,
            x,
            z,
            [
                (h + 0.09 * k, 0.039 * k),
                (h + 0.14 * k, 0.051 * k),
                (h + 0.15 * k, 0.044 * k),
            ],
            12,
        )

    for cx, cz in (
        (-8.5, -7),
        (-9.3, -0.8),
        (-7.5, 9.8),
        (6, -10.6),
        (8.9, 5.4),
        (8.8, 9.5),
    ):
        sites = []
        for i in range(28):
            x = cx + rng.uniform(-1.6, 1.6)
            z = cz + rng.uniform(-2.25, 2.25)
            r = rng.uniform(0.24, 0.48)
            if any(
                (x - px) ** 2 + (z - pz) ** 2 < (0.80 * (r + pr)) ** 2
                for px, pz, pr in sites
            ):
                continue
            sites.append((x, z, r))
            height = WATER + rng.uniform(0.02, 0.43)
            leaf(x, z, r, height, rng.uniform(-0.12, 0.12))
            if len(sites) in (3, 8, 13):
                flower(
                    x + 0.36,
                    z + 0.10,
                    height + rng.uniform(0.18, 0.44),
                    rng.uniform(0.85, 1.14),
                )
    art.save(dest)
