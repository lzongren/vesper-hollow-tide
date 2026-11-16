"""Build a six-sided oil lantern in metres around the original road fixture pivot."""

from collections import defaultdict
from math import cos, pi, sin, tau
from bind_pilgrim import Output, cross, unit


def build(textures, paper_image, destination):
    glb = Output()
    glb.doc.update(meshes=[], nodes=[], scenes=[{"nodes": []}])
    glb.doc["asset"]["generator"] = "Vesper lotus road lamp"
    batches = defaultdict(lambda: ([], [], [], []))

    def material(name, path, tint, rough, metal=0, normal=None, glow=None):
        image = glb.image(path.read_bytes(), "image/jpeg", name + "Color")
        mat = dict(
            name=name,
            doubleSided=True,
            pbrMetallicRoughness=dict(
                baseColorTexture=image,
                baseColorFactor=[*tint, 1],
                metallicFactor=metal,
                roughnessFactor=rough,
            ),
        )
        if normal:
            mat["normalTexture"] = dict(
                glb.image(normal.read_bytes(), "image/jpeg", name + "Normal"),
                scale=0.42,
            )
        if glow:
            mat.update(emissiveFactor=glow, emissiveTexture=image)
        glb.doc["materials"].append(mat)
        return len(glb.doc["materials"]) - 1

    stone = material(
        "LotusStone",
        textures / "rock-color.jpg",
        (0.33, 0.40, 0.43),
        0.84,
        normal=textures / "rock-normal.jpg",
    )
    bronze = material(
        "LotusBronze",
        textures / "metal-color.jpg",
        (0.14, 0.29, 0.24),
        0.54,
        0.66,
        textures / "metal-normal.jpg",
    )
    gilt = material(
        "LotusGilt", textures / "metal-color.jpg", (0.68, 0.43, 0.17), 0.46, 0.70
    )
    silk = material(
        "LotusScreen", paper_image, (0.91, 0.78, 0.62), 0.88, glow=(0.57, 0.32, 0.135)
    )

    def grid(mat, nx, ny, point, uv=lambda u, v: (u, 1 - v)):
        positions, normals, tex, indices = batches[mat]
        base = len(positions)
        for j in range(ny + 1):
            v = j / ny
            for i in range(nx + 1):
                u = i / nx
                p = point(u, v)
                du = tuple(
                    a - b
                    for a, b in zip(
                        point(min(1, u + 0.001), v), point(max(0, u - 0.001), v)
                    )
                )
                dv = tuple(
                    a - b
                    for a, b in zip(
                        point(u, min(1, v + 0.001)), point(u, max(0, v - 0.001))
                    )
                )
                positions.append(p)
                normals.append(unit(cross(du, dv)))
                tex.append(uv(u, v))
                if i and j:
                    n = base + j * (nx + 1) + i
                    indices.extend((n - nx - 2, n - nx - 1, n, n - nx - 2, n, n - 1))

    def radial(a, r, h):
        return r * sin(a), h, r * cos(a)

    def polygon(side, u, r, h):
        a, b = side * tau / 6, (side + 1) * tau / 6
        return (
            r * ((1 - u) * sin(a) + u * sin(b)),
            h,
            r * ((1 - u) * cos(a) + u * cos(b)),
        )

    def turning(mat, rings, flutes=0):
        for (h0, r0), (h1, r1) in zip(rings, rings[1:]):

            def turned(u, v):
                a = tau * u
                r = r0 + (r1 - r0) * v
                if flutes:
                    r *= 1 - 0.054 * (0.5 + 0.5 * cos(a * flutes)) ** 2
                return radial(a, r, h0 + (h1 - h0) * v)

            grid(mat, 72, 1, turned, lambda u, v: (u * 3.5, (h0 + (h1 - h0) * v) * 2))

    def hex_band(mat, rings):
        for side in range(6):
            for (h0, r0), (h1, r1) in zip(rings, rings[1:]):
                grid(
                    mat,
                    1,
                    1,
                    lambda u, v: polygon(
                        side, u, r0 + (r1 - r0) * v, h0 + (h1 - h0) * v
                    ),
                    lambda u, v: (u, (h0 + (h1 - h0) * v) * 2),
                )

    def cord(mat, path, radius, steps=14):
        def tube(u, v):
            p = path(v)
            axis = unit(
                tuple(
                    a - b
                    for a, b in zip(path(min(1, v + 0.001)), path(max(0, v - 0.001)))
                )
            )
            n = unit(cross(axis, (0, 1, 0) if abs(axis[1]) < 0.96 else (1, 0, 0)))
            m = cross(axis, n)
            return tuple(
                p[i] + radius * (n[i] * cos(tau * u) + m[i] * sin(tau * u))
                for i in range(3)
            )

        grid(mat, 8, steps, tube)

    def petals(mat, count, y, height, radius0, radius1, relief, start=0):
        for k in range(count):

            def petal(u, v):
                a = tau * (k + start) / count + (u - 0.5) * tau / count * 0.98 * (
                    0.06 + 0.94 * sin(pi * v) ** 0.62
                )
                ridge = sin(pi * v) ** 0.72 * (0.38 + 0.62 * sin(pi * u) ** 0.64)
                r = radius0 + (radius1 - radius0) * v + relief * ridge
                return radial(a, r, y + height * v)

            grid(mat, 10, 12, petal)
            cord(mat, lambda v: petal(0.5, v), 0.0027, 10)

    # A fluted shaft sits between two lotus courses instead of a solid tall block.
    hex_band(
        stone,
        [
            (-0.015, 0.46),
            (0.048, 0.46),
            (0.075, 0.435),
            (0.095, 0.408),
            (0.13, 0.408),
            (0.152, 0.381),
            (0.159, 0.29),
        ],
    )
    turning(
        stone,
        [
            (0.15, 0.29),
            (0.19, 0.326),
            (0.24, 0.31),
            (0.27, 0.25),
            (0.34, 0.189),
            (0.37, 0.17),
        ],
    )
    petals(stone, 14, 0.18, 0.18, 0.307, 0.173, 0.045)
    turning(
        stone,
        [
            (0.35, 0.172),
            (0.39, 0.183),
            (0.416, 0.168),
            (0.441, 0.141),
            (0.82, 0.139),
            (0.87, 0.166),
            (0.9, 0.18),
        ],
        18,
    )
    turning(
        stone,
        [(0.89, 0.18), (0.94, 0.205), (1.01, 0.266), (1.10, 0.337), (1.13, 0.341)],
    )
    petals(stone, 14, 0.91, 0.205, 0.19, 0.333, 0.049, 0.5)
    turning(bronze, [(1.108, 0.327), (1.137, 0.355), (1.158, 0.352), (1.175, 0.316)])
    hex_band(
        bronze,
        [(1.155, 0.29), (1.185, 0.394), (1.21, 0.407), (1.235, 0.391), (1.269, 0.354)],
    )
    hex_band(gilt, [(1.207, 0.407), (1.215, 0.408), (1.218, 0.403)])
    # Six narrow fretwork screens enclose the painted paper drum.
    for side in range(6):
        grid(
            silk,
            1,
            1,
            lambda u, v: polygon(side, u, 0.346, 1.249 + 0.564 * v),
            lambda u, v: ((side + u) / 6, 1 - v),
        )
        cord(
            bronze, lambda t: radial(side * tau / 6, 0.357, 1.238 + 0.614 * t), 0.018, 2
        )
        for y in (1.259, 1.317, 1.734, 1.803):
            cord(bronze, lambda u: polygon(side, u, 0.36, y), 0.009, 2)
        for col in range(4):
            # Stepped thunder-key fret bends across each upper transom.
            points = [
                (col / 4, 1.738),
                ((col + 0.20) / 4, 1.738),
                ((col + 0.20) / 4, 1.778),
                ((col + 0.76) / 4, 1.778),
                ((col + 0.76) / 4, 1.752),
                ((col + 0.48) / 4, 1.752),
            ]
            for (u0, y0), (u1, y1) in zip(points, points[1:]):
                cord(
                    gilt,
                    lambda t: polygon(
                        side, u0 + (u1 - u0) * t, 0.36, y0 + (y1 - y0) * t
                    ),
                    0.006,
                    1,
                )
        for i in range(1, 6):
            cord(
                gilt, lambda v: polygon(side, i / 6, 0.36, 1.269 + 0.045 * v), 0.004, 1
            )

    hex_band(bronze, [(1.797, 0.35), (1.82, 0.395), (1.843, 0.397), (1.864, 0.442)])
    # Each roof bay sags between raised hip ribs. The corners curl above the eaves.
    for side in range(6):

        def canopy(u, v):
            corner = abs(2 * u - 1) ** 2.6
            r = (0.486 + 0.062 * corner) * (1 - v) + 0.064 * v
            y = 1.854 + 0.289 * v**1.85 + 0.095 * corner * (1 - v) ** 2
            return polygon(side, u, r, y)

        grid(bronze, 18, 12, canopy, lambda u, v: (u, 1 - v))
        cord(gilt, lambda t: canopy(t, 0), 0.006, 20)
        for i in range(1, 7):
            cord(bronze, lambda t: canopy(i / 7, t), 0.006, 12)
        cord(bronze, lambda t: canopy(0, t), 0.013, 14)
        a = side * tau / 6
        cord(
            bronze,
            lambda t: radial(a, 0.524 + 0.052 * t, 1.936 + 0.078 * t * t),
            0.011,
            12,
        )
        # A small suspended bell with a flared lip marks each roof corner.
        cx, _, cz = radial(a, 0.525, 0)
        cord(gilt, lambda t: (cx, 1.94 - 0.071 * t, cz), 0.0035, 2)

        def bell(u, v):
            r = 0.013 + 0.020 * (1 - v) ** 2
            return cx + r * sin(tau * u), 1.824 + 0.048 * v, cz + r * cos(tau * u)

        grid(gilt, 16, 6, bell)
        cord(bronze, lambda t: (cx, 1.831 - 0.016 * t, cz), 0.006, 2)
    turning(
        bronze,
        [(2.128, 0.066), (2.151, 0.079), (2.17, 0.079), (2.186, 0.050), (2.206, 0.042)],
    )
    petals(gilt, 8, 2.175, 0.105, 0.046, 0.018, 0.023)
    turning(gilt, [(2.256, 0.025), (2.285, 0.031), (2.31, 0.019), (2.347, 0.002)])

    for idx, (positions, normals, tex, indices) in batches.items():
        name = glb.doc["materials"][idx]["name"]
        attrs = dict(
            POSITION=glb.data(positions, "VEC3", bounds=True),
            NORMAL=glb.data(normals, "VEC3"),
            TEXCOORD_0=glb.data(tex, "VEC2"),
        )
        prim = dict(
            attributes=attrs,
            material=idx,
            indices=glb.data([(n,) for n in indices], "SCALAR", 5125),
        )
        node = len(glb.doc["meshes"])
        glb.doc["meshes"].append(dict(name=name, primitives=[prim]))
        glb.doc["nodes"].append(dict(name=name, mesh=node))
        glb.doc["scenes"][0]["nodes"].append(node)
    glb.save(destination)
