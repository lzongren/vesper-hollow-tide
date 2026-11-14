"""Bellwarden's masked headpiece and robe, in the local rig's metre-space bind pose."""

from math import cos, exp, pi, sin, sqrt, tau


def add_regalia(out, joints, textures):
    def material(name, color, metal, rough, image=None, normal=None, cutout=False):
        pbr = dict(
            baseColorFactor=[*color, 1], metallicFactor=metal, roughnessFactor=rough
        )
        entry = dict(name=name, doubleSided=True, pbrMetallicRoughness=pbr)
        for path, props, key in [
            (image, pbr, "baseColorTexture"),
            (normal, entry, "normalTexture"),
        ]:
            if path:
                mime = "image/png" if path.endswith(".png") else "image/jpeg"
                props[key] = out.image((textures / path).read_bytes(), mime, name + key)
        if cutout:
            entry.update(alphaMode="MASK", alphaCutoff=0.52)
        out.doc["materials"].append(entry)
        return len(out.doc["materials"]) - 1

    damask = material(
        "Oxide red dragon damask",
        (0.67, 0.53, 0.36),
        0.16,
        0.69,
        "dragon-mantle.jpg",
        "pilgrim-brocade-normal.jpg",
    )
    silk = material(
        "Ink blue shot silk",
        (0.026, 0.069, 0.064),
        0.13,
        0.55,
        normal="pilgrim-brocade-normal.jpg",
    )
    gilt = material("Gilt bronze wire", (0.46, 0.28, 0.079), 0.72, 0.44)
    jade = material("Clouded nephrite", (0.14, 0.32, 0.23), 0.13, 0.37)
    mask = material(
        "Repousse ritual face",
        (0.9, 0.80, 0.61),
        0.5,
        0.48,
        "warden-mask.png",
        cutout=True,
    )
    buckets = {}

    def patch(slot, cols, rows, sample):
        positions, normals, uv, bone_ids, weights, triangles = buckets.setdefault(
            slot, ([], [], [], [], [], [])
        )
        first = len(positions)
        for j in range(rows + 1):
            v = j / rows
            for i in range(cols + 1):
                u = i / cols
                p, tex, skin = sample(u, v)
                positions.append(p)
                uv.append(tex)
                bone_ids.append(
                    tuple([joints[b] for b, w in skin] + [0] * (4 - len(skin)))
                )
                weights.append(tuple([w for b, w in skin] + [0.0] * (4 - len(skin))))
                a = sample(min(1, u + 0.0002), v)[0]
                b = sample(max(0, u - 0.0002), v)[0]
                c = sample(u, min(1, v + 0.0002))[0]
                d = sample(u, max(0, v - 0.0002))[0]
                x, y, z = (a[k] - b[k] for k in range(3))
                h, l, m = (c[k] - d[k] for k in range(3))
                normal = (y * m - z * l, z * h - x * m, x * l - y * h)
                length = sqrt(sum(k * k for k in normal))
                normals.append(
                    tuple(k / length for k in normal) if length else (0, 1, 0)
                )
        for j in range(rows):
            for i in range(cols):
                a = first + j * (cols + 1) + i
                triangles.extend(
                    [(a, a + 1, a + cols + 1), (a + 1, a + cols + 2, a + cols + 1)]
                )

    head = [("head", 1.0)]

    def skirt(theta, y):
        t = max(0, min(1, (y - 0.25) / 1.25))
        width = 0.259 + 0.18 * (1 - t) ** 1.35 + 0.07 * exp(-(((t - 0.87) / 0.14) ** 2))
        depth = (
            0.178 + 0.103 * (1 - t) ** 1.23 + 0.033 * exp(-(((t - 0.85) / 0.18) ** 2))
        )
        pleat = (0.020 + 0.016 * (1 - t)) * cos(14 * theta + 0.7 * t)
        return ((width + pleat) * sin(theta), y, 0.02 + (depth + pleat) * cos(theta))

    def cloth_skin(theta, y):
        if y > 1.02:
            f = min(1, (y - 1.02) / 0.28)
            return [("pelvis", 1 - f), ("spine_05", f)]
        leg = "thigh_l" if sin(theta) >= 0 else "thigh_r"
        f = min(0.83, max(0, (1.02 - y) / 0.49))
        return [("pelvis", 1 - f), (leg, f)]

    def body(u, v):
        theta = tau * u
        y = 0.32 + 1.17 * v - 0.042 * (1 - v) ** 3 * cos(theta * 8)
        return skirt(theta, y), (u * 3, 1 - v), cloth_skin(theta, y)

    patch(silk, 112, 30, body)

    # Split panels overlap the blue robe and allow each thigh to carry its hem.
    for side in range(4):
        center = side * pi / 2

        def panel(u, v, center=center):
            theta = center + (u - 0.5) * (0.94 + 0.24 * v)
            y = 0.245 + 1.239 * v + 0.075 * (abs(2 * u - 1) ** 2) * (1 - v) ** 4
            x, y, z = skirt(theta, y)
            overlay = 0.035 + 0.017 * cos(u * tau) * sin(pi * v)
            return (
                (x + overlay * sin(theta), y, z + overlay * cos(theta)),
                (u, 1 - v),
                cloth_skin(theta, y),
            )

        patch(damask, 26, 34, panel)
        for edge in (0, 1):

            def piping(u, v, edge=edge):
                t = (0.018 + 0.017 * u) if edge == 0 else (0.965 + 0.017 * u)
                (x, y, z), tex, skin = panel(t, v)
                return (x * 1.012, y, z * 1.012), tex, skin

            patch(gilt, 2, 36, piping)

    # A raised belt and collar finish the robe where it meets the armour.
    for y0, h, radius, depth in [
        (1.02, 0.082, 0.30, 0.235),
        (1.46, 0.065, 0.197, 0.158),
    ]:

        def band(u, v):
            angle = tau * u
            return (
                (radius * sin(angle), y0 + h * v, 0.02 + depth * cos(angle)),
                (u * 4, 1 - v),
                cloth_skin(angle, y0 + h * v),
            )

        patch(gilt, 64, 3, band)

    def face(u, v):
        x = (u - 0.5) * 2
        h = (v - 0.5) * 2

        def relief(cx, cy, sx, sy):
            return exp(-(((x - cx) / sx) ** 2) - ((h - cy) / sy) ** 2)

        depth = (
            0.089 * cos(x * 1.25)
            - 0.037 * x * x
            - 0.04 * h * h
            + 0.038 * relief(0, -0.03, 0.115, 0.45)
            + 0.033 * relief(0, -0.18, 0.20, 0.12)
            + 0.018 * relief(abs(x), 0.39, 0.72, 0.11)
            - 0.02 * relief(abs(x) - 0.43, 0.18, 0.28, 0.15)
            + 0.019 * relief(0, -0.46, 0.36, 0.11)
        )
        return (
            (0.171 * sin(1.22 * x) / sin(1.22), 1.686 + 0.235 * h, 0.147 + depth),
            (u, 1 - v),
            head,
        )

    patch(mask, 56, 68, face)

    def halo(u, v, rx, ry, wire, z):
        a = -tau * u
        b = tau * v
        return (
            (
                (rx + wire * cos(b)) * cos(a),
                1.73 + (ry + wire * cos(b)) * sin(a),
                z + wire * sin(b),
            ),
            (u, v),
            head,
        )

    for rx, ry, wire, z in [
        (0.288, 0.338, 0.015, -0.078),
        (0.255, 0.309, 0.006, -0.071),
    ]:
        patch(gilt, 96, 10, lambda u, v: halo(u, v, rx, ry, wire, z))

    def bead(cx, cy, cz, rx, ry, rz, slot):
        def shell(u, v):
            a = tau * u
            b = (v - 0.5) * pi
            return (
                (
                    cx + rx * sin(a) * cos(b),
                    cy + ry * sin(b),
                    cz + rz * cos(a) * cos(b),
                ),
                (u, 1 - v),
                head,
            )

        patch(slot, 12, 10, shell)

    for side in (-1, 1):
        for i in range(4):
            x = side * (0.189 + 0.025 * i)
            top = 1.73 + 0.334 * sqrt(1 - (x / 0.288) ** 2)
            bottom = top - 0.242 - 0.052 * i
            z = -0.061 + 0.009 * i

            def string(u, v):
                a = tau * u
                return (
                    (
                        x + 0.004 * sin(a),
                        bottom + (top - bottom) * v,
                        z + 0.004 * cos(a),
                    ),
                    (u, v),
                    head,
                )

            patch(gilt, 8, 2, string)
            bead(x, bottom, z, 0.014, 0.026, 0.014, jade)
    bead(0, 2.077, -0.073, 0.026, 0.045, 0.018, jade)

    for slot, (p, n, uv, ids, w, tris) in buckets.items():
        attrs = dict(
            POSITION=out.data(p, "VEC3", bounds=True),
            NORMAL=out.data(n, "VEC3"),
            TEXCOORD_0=out.data(uv, "VEC2"),
            JOINTS_0=out.data(ids, "VEC4", 5123),
            WEIGHTS_0=out.data(w, "VEC4"),
        )
        indices = out.data([(i,) for tri in tris for i in tri], "SCALAR", 5125)
        out.doc["meshes"][0]["primitives"].append(
            dict(attributes=attrs, indices=indices, material=slot)
        )
