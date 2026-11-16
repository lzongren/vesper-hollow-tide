"""Construct the hipped roofs, bell chamber and terraced base in glTF metres."""

from collections import defaultdict
from math import cos, pi, sin
from pathlib import Path
from bind_pilgrim import Output, cross, unit


def bake(art, dest):
    glb = Output()
    glb.doc.update(meshes=[], nodes=[], scenes=[{"nodes": []}])
    glb.doc["asset"]["generator"] = "Vesper mountain bell hall"
    batches = defaultdict(lambda: ([], [], [], [], []))

    def material(name, path, normal=None, rough=0.78, metal=0):
        pbr = {
            "roughnessFactor": rough,
            "metallicFactor": metal,
            "baseColorTexture": glb.image(
                (art / path).read_bytes(), "image/jpeg", name + "Color"
            ),
        }
        mat = dict(name=name, doubleSided=True, pbrMetallicRoughness=pbr)
        if normal:
            mat["normalTexture"] = dict(
                glb.image((art / normal).read_bytes(), "image/jpeg", name + "Normal"),
                scale=0.66,
            )
        glb.doc["materials"].append(mat)
        return len(glb.doc["materials"]) - 1

    tile = material("Kiln tiles", "rock-color.jpg", "rock-normal.jpg", 0.53)
    stone = material("Terrace masonry", "rock-color.jpg", "rock-normal.jpg")
    timber = material("Smoke aged cedar", "wood-color.jpg", "wood-normal.jpg")
    paint = material("Paired dragon fascia", "belfry-dragon-beam.jpg")
    bronze = material(
        "Cast ridge bronze", "metal-color.jpg", "metal-normal.jpg", 0.56, 0.53
    )
    mural = material("Sanctum screen", "tide-icon.jpg")
    plaque = material("Bell hall tablet", "belfry-plaque.jpg", rough=0.62)
    paper = material("Clerestory silk", "belfry-paper.jpg")

    def patch(slot, pts, uv, shade=(1, 1, 1)):
        p, n, t, c, idx = batches[slot]
        start = len(p)
        normal = unit(
            cross(
                tuple(pts[1][i] - pts[0][i] for i in range(3)),
                tuple(pts[2][i] - pts[0][i] for i in range(3)),
            )
        )
        p.extend(pts)
        n.extend([normal] * 4)
        t.extend(uv)
        c.extend([shade] * 4)
        idx.extend([start, start + 1, start + 2, start, start + 2, start + 3])

    image_uv = [(0, 1), (1, 1), (1, 0), (0, 0)]

    def panel(mat, x, y, z, width, height, shade=(1, 1, 1)):
        patch(
            mat,
            [
                (x - width / 2, y, z),
                (x + width / 2, y, z),
                (x + width / 2, y + height, z),
                (x - width / 2, y + height, z),
            ],
            image_uv,
            shade,
        )

    def box(mat, x, y, z, w, h, d, shade):
        corners = [
            (x + a * w / 2, y + b * h / 2, z + c * d / 2)
            for a, b, c in [
                (-1, -1, -1),
                (1, -1, -1),
                (1, 1, -1),
                (-1, 1, -1),
                (-1, -1, 1),
                (1, -1, 1),
                (1, 1, 1),
                (-1, 1, 1),
            ]
        ]
        for face in [
            (4, 5, 6, 7),
            (1, 0, 3, 2),
            (0, 4, 7, 3),
            (5, 1, 2, 6),
            (7, 6, 2, 3),
            (0, 1, 5, 4),
        ]:
            pts = [corners[i] for i in face]
            a, b, e = pts[0], pts[1], pts[3]
            length = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
            height = sum((x - y) ** 2 for x, y in zip(a, e)) ** 0.5
            uv = [
                (0, height / 1.7),
                (length / 1.7, height / 1.7),
                (length / 1.7, 0),
                (0, 0),
            ]
            patch(mat, pts, uv, shade)

    ash = (0.46, 0.51, 0.51)
    red = (0.45, 0.15, 0.083)
    dark = (0.21, 0.17, 0.13)
    gold = (0.72, 0.6, 0.39)
    # Individual stretcher courses turn both corners. The foundation continues
    # below the upper court to meet the sloping ground at the back of the hall.
    for row in range(8):
        for z in (-3.38, 2.81):
            left = -5.72
            i = 0
            while left < 5.71:
                right = min(5.72, left + (1.02 if row % 2 and i == 0 else 1.74))
                noise = 0.83 + 0.15 * ((row * 13 + i * 7) % 11) / 10
                box(
                    stone,
                    (left + right) / 2,
                    -3.37 + row * 0.59,
                    z,
                    right - left - 0.014,
                    0.578,
                    0.43,
                    tuple(k * noise for k in ash),
                )
                left = right
                i += 1
        for x in (-5.52, 5.52):
            for j in range(4):
                box(
                    stone,
                    x,
                    -3.37 + row * 0.59,
                    -2.49 + j * 1.45,
                    0.41,
                    0.579,
                    1.43,
                    ash,
                )
    box(stone, 0, 0.96, -0.28, 11.52, 0.27, 6.65, ash)
    for i in range(6):
        box(
            stone,
            0,
            0.09 + i * 0.087,
            5.25 - i * 0.43,
            6.36,
            0.18 + i * 0.174,
            0.465,
            ash,
        )
    box(timber, 0, 3.02, -2.95, 10.8, 3.84, 0.19, dark)
    panel(mural, 0, 1.29, -2.83, 6.8, 3.42)
    for x in [-5.24, -3.56, 3.56, 5.24]:
        box(timber, x, 3.06, -2.69, 0.25, 3.94, 0.34, red)
    for x in [-5.36, 5.36]:
        box(timber, x, 3.0, -0.25, 0.18, 3.82, 5.54, dark)
    # Timber-framed side bays break the broad gable walls into recessed
    # lights and sills, readable on the oblique approach from the court.
    for side in (-1, 1):
        x = side * 5.47
        for bay in range(4):
            z = -2.32 + bay * 1.36
            patch(
                paper,
                [
                    (x, 1.95, z - 0.55),
                    (x, 1.95, z + 0.55),
                    (x, 3.66, z + 0.55),
                    (x, 3.66, z - 0.55),
                ],
                image_uv,
                (0.58, 0.49, 0.39) if bay % 3 else (0.88, 0.70, 0.53),
            )
            for dz in (-0.57, -0.23, 0.23, 0.57):
                box(timber, x + side * 0.03, 2.81, z + dz, 0.09, 1.85, 0.046, red)
            for h in (1.9, 2.4, 3.14, 3.70):
                box(timber, x + side * 0.05, h, z, 0.12, 0.068, 1.21, dark)
            box(timber, x + side * 0.045, 3.04, z - 0.64, 0.16, 3.8, 0.12, red)
        box(stone, x, 1.26, -0.26, 0.32, 0.23, 5.63, ash)
    # The yoke and the vertical hanger meet the crown of the imported bell.
    box(timber, 0, 4.79, 0.70, 7.1, 0.40, 0.42, dark)
    box(bronze, 0, 4.43, 0.70, 0.085, 0.47, 0.085, gold)
    panel(plaque, 0, 4.62, 3.24, 3.08, 0.93)
    for y in [4.59, 5.57]:
        box(bronze, 0, y, 3.23, 3.2, 0.056, 0.07, gold)
    for x in [-1.58, 1.58]:
        box(bronze, x, 5.08, 3.23, 0.055, 1.02, 0.07, gold)
    for y, w, d in [(5.65, 12.6, 6.9), (8.09, 8.8, 4.2)]:
        box(timber, 0, y, 0, w, 0.38, d, dark)
        panel(paint, 0, y - 0.13, d / 2 + 0.012, w, 0.28)
    # Seven recessed window bays under the upper eaves.
    box(timber, 0, 7.38, 0, 7.72, 1.40, 3.60, dark)
    for i in range(-3, 4):
        x = i * 1.04
        panel(paper, x, 6.85, 1.815, 0.91, 0.99, (0.8, 0.63, 0.38))
        for dx in [-0.44, -0.22, 0, 0.22, 0.44]:
            box(timber, x + dx, 7.35, 1.85, 0.04, 1.06, 0.07, red)
        for dy in [-0.31, 0.06, 0.33]:
            box(timber, x, 7.35 + dy, 1.85, 0.94, 0.042, 0.07, red)

    def roof(width, depth, ridge, y, height, rows):
        # Four ruled slopes taper to a horizontal ridge. Each arc follows one
        # rounded cover tile; overlaps cast shadows across the pan below it.
        ring = [(-width, depth), (width, depth), (width, -depth), (-width, -depth)]
        crest = [(-ridge, 0), (ridge, 0), (ridge, 0), (-ridge, 0)]

        def point(edge, u, t):
            j = (edge + 1) % 4
            ax, az = ring[edge]
            bx, bz = ring[j]
            cx, cz = crest[edge]
            dx, dz = crest[j]
            ex, ez = ax + (bx - ax) * u, az + (bz - az) * u
            topx, topz = cx + (dx - cx) * u, cz + (dz - cz) * u
            lift = 0.58 * abs(u * 2 - 1) ** 5 * t**2
            return (
                topx + (ex - topx) * t,
                y + height * (1 - t) ** 1.55 + lift,
                topz + (ez - topz) * t,
            )

        for edge in range(4):
            count = round((2 * width if edge % 2 == 0 else 2 * depth) / 0.27)
            for course in range(rows):
                top = max(0.009, course / rows)
                base = (course + 1) / rows
                for col in range(count):
                    shade = (
                        0.60 + 0.34 * ((col * 31 + course * 17 + edge * 41) % 23) / 22
                    )
                    tint = (shade * 0.37, shade * 0.50, shade * 0.47)
                    for k in range(5):
                        pts = []
                        uv = []
                        for h, t in [(k, base), (k + 1, base), (k + 1, top), (k, top)]:
                            u = (col + h / 5) / count
                            x, yy, z = point(edge, u, t)
                            crown = 0.073 * (0.5 + 0.5 * cos(h / 5 * 2 * pi)) ** 1.4
                            yy += crown + 0.045 * (t - top) / (base - top)
                            pts.append((x, yy, z))
                            uv.append(
                                (
                                    (col + h / 5) * 0.27,
                                    course + (t - top) / (base - top),
                                )
                            )
                        patch(tile, pts, uv, tint)
            # Upturned hip ridge. Bronze collars interrupt a dark fired-clay core.
            for step in range(24):
                t = (step + 0.5) / 24
                x, yy, z = point(edge, 0, t)
                rr = 0.155 + 0.035 * t
                box(
                    bronze if step % 5 == 0 else tile,
                    x,
                    yy + 0.085,
                    z,
                    rr * 2,
                    0.19,
                    rr * 2,
                    gold if step % 5 == 0 else (0.37, 0.43, 0.39),
                )
        box(
            tile,
            0,
            y + height + 0.09,
            0,
            2 * ridge + 0.47,
            0.26,
            0.34,
            (0.36, 0.41, 0.37),
        )
        for sign in [-1, 1]:
            for i in range(7):
                box(
                    bronze,
                    sign * (ridge + 0.06 + i * 0.065),
                    y + height + 0.21 + i * i * 0.011,
                    0,
                    0.19,
                    0.20,
                    0.21,
                    gold,
                )

    roof(7.40, 4.42, 3.35, 5.82, 1.39, 10)
    roof(5.10, 2.91, 2.27, 8.26, 1.77, 8)

    for slot, (p, n, uv, color, indices) in batches.items():
        name = glb.doc["materials"][slot]["name"].replace(" ", "")
        attrs = dict(
            POSITION=glb.data(p, "VEC3", bounds=True),
            NORMAL=glb.data(n, "VEC3"),
            TEXCOORD_0=glb.data(uv, "VEC2"),
            COLOR_0=glb.data(color, "VEC3"),
        )
        prim = dict(
            attributes=attrs,
            indices=glb.data([(i,) for i in indices], "SCALAR", 5125),
            material=slot,
        )
        idx = len(glb.doc["meshes"])
        glb.doc["meshes"].append(dict(name=name, primitives=[prim]))
        glb.doc["nodes"].append(dict(name=name, mesh=idx))
        glb.doc["scenes"][0]["nodes"].append(idx)
    glb.save(dest)


if __name__ == "__main__":
    import sys

    bake(Path(sys.argv[1]), Path(sys.argv[2]))
