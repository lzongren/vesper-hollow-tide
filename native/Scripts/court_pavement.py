"""Cut the Bellwarden's forecourt in metres, with open drains and chipped slab edges."""

from math import exp, sin
from random import Random

from bind_pilgrim import Output, cross, unit


def bake(destination):
    rng = Random(1631)
    glb = Output()
    glb.doc["asset"]["generator"] = "Vesper temple forecourt"
    glb.doc["meshes"][0]["name"] = "BelfryCourt"
    glb.doc["nodes"] = [{"mesh": 0, "name": "BelfryCourt"}]
    pools = [(-3.6, 1, 4, 1), (3.3, 3, 2, 1.4), (2, -4, 4, 1.3), (-8, 5, 3, 0.95)]
    batches = {}
    for name in ("Paving", "DrainIron"):
        glb.doc["materials"].append({"name": name, "pbrMetallicRoughness": {}})
        batches[name] = ([], [], [], [], [])
    count = 0

    def wetness(x, z):
        return min(
            1,
            sum(
                exp(-(((x - cx) / sx) ** 2) - ((z - cz) / sz) ** 2)
                for cx, cz, sx, sz in pools
            )
            + 0.10 * (1 + sin(x * 0.8 + z * 0.4)),
        )

    def polygon(name, pts, tint, offset, face):
        pos, normals, uv, rgba, indices = batches[name]
        start = len(pos)
        a, b, c = pts[:3]
        n = unit(
            cross(
                tuple(b[i] - a[i] for i in range(3)),
                tuple(c[i] - a[i] for i in range(3)),
            )
        )
        for x, y, z in pts:
            pos.append((x, y, z))
            normals.append(n)
            uv.append((offset[0] + x / 1.85, offset[1] + z / 1.85))
            rgba.append((*[v * face for v in tint], wetness(x, z)))
        for j in range(1, len(pts) - 1):
            indices.extend((start, start + j, start + j + 1))

    def block(x1, x2, z1, z2, top, tone, name="Paving", bevel=0.015):
        # Eight-point arris. The footprint remains inside its own mortar bed.
        cx, cz = (x1 + x2) / 2, (z1 + z2) / 2
        corners = [
            min(rng.uniform(0.014, 0.090), (x2 - x1) / 5, (z2 - z1) / 5)
            for _ in range(4)
        ]
        a, b, c, d = corners
        outline = [
            (x1 + a, z1),
            (x1, z1 + a),
            (x1, z2 - b),
            (x1 + b, z2),
            (x2 - c, z2),
            (x2, z2 - c),
            (x2, z1 + d),
            (x2 - d, z1),
        ]
        uv_shift = (rng.random() * 4, rng.random() * 4)
        tint = (tone * 0.85, tone * 0.94, tone)
        # The irregular lip slopes down to a dark sidewall. A slight planar
        # fall varies the specular response without creating uneven collision.
        pitch, roll = rng.uniform(-0.006, 0.006), rng.uniform(-0.005, 0.005)
        rim, lip, base = [], [], []
        for x, z in outline:
            h = top + (x - cx) * pitch + (z - cz) * roll
            rim.append(
                (
                    x - (x - cx) * bevel / max(0.02, (x2 - x1) / 2),
                    h,
                    z - (z - cz) * bevel / max(0.02, (z2 - z1) / 2),
                )
            )
            lip.append((x, h - bevel, z))
            base.append((x, -0.086, z))
        # Fan from the centre keeps interpolated wetness continuous across broad slabs.
        for i in range(8):
            j = (i + 1) % 8
            polygon(name, [(cx, top, cz), rim[i], rim[j]], tint, uv_shift, 1)
            polygon(name, [rim[j], rim[i], lip[i], lip[j]], tint, uv_shift, 0.83)
            polygon(name, [lip[j], lip[i], base[i], base[j]], tint, uv_shift, 0.53)

    def courses(x1, x2, z1, z2, rows, short, long, light=1):
        nonlocal count
        for row in range(rows):
            lo = z1 + (z2 - z1) * row / rows
            hi = z1 + (z2 - z1) * (row + 1) / rows
            x = x1
            while x < x2 - 0.01:
                width = rng.uniform(short, long)
                if x == x1 and row % 2:
                    width *= 0.51
                end = min(x2, x + width)
                if x2 - end < 0.44:
                    end = x2
                block(
                    x + 0.006,
                    end - 0.006,
                    lo + 0.006,
                    hi - 0.006,
                    rng.uniform(-0.004, 0.005),
                    light * rng.uniform(0.56, 0.98),
                )
                count += 1
                x = end

    # Two parallel open channels and stone kerbs divide the side aisles from
    # the processional lane. The gratings sit over an actual gap in the pavers.
    for lo, hi, rows, tone in [
        (-14, -4.46, 12, 0.87),
        (-4.46, -4.12, 1, 1.1),
        (-3.88, 3.88, 11, 1),
        (4.12, 4.46, 1, 1.1),
        (4.46, 14, 12, 0.87),
    ]:
        courses(-14.6, 14.6, lo, hi, rows, 0.99, 1.94, tone)
    for side in (-1, 1):
        z = 4 * side
        for i in range(292):
            x = -14.6 + i * 0.1
            block(
                x + 0.012,
                x + 0.055,
                z - 0.122,
                z + 0.122,
                -0.013,
                0.32,
                "DrainIron",
                bevel=0.003,
            )

    for slot, (pos, normals, uv, color, indices) in enumerate(batches.values()):
        attrs = {
            "POSITION": glb.data(pos, "VEC3", bounds=True),
            "NORMAL": glb.data(normals, "VEC3"),
            "TEXCOORD_0": glb.data(uv, "VEC2"),
            "COLOR_0": glb.data(color, "VEC4"),
        }
        glb.doc["meshes"][0]["primitives"].append(
            {
                "attributes": attrs,
                "indices": glb.data([(i,) for i in indices], "SCALAR", 5125),
                "material": slot,
            }
        )
    glb.save(destination)
    return count
