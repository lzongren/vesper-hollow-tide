"""Fit a damask wedding coat and two layered feather fans to the combat rig."""

from math import sin, cos, pi, tau
from bind_pilgrim import cross, unit


def add_dress(out, bones, rest, source):
    def material(name, rgb, rough, metal, image=None, cutout=False):
        pbr = dict(
            baseColorFactor=[*rgb, 1], roughnessFactor=rough, metallicFactor=metal
        )
        mat = dict(name=name, pbrMetallicRoughness=pbr, doubleSided=True)
        if image:
            mime = "image/png" if image.endswith(".png") else "image/jpeg"
            pbr["baseColorTexture"] = out.image(
                (source / image).read_bytes(), mime, name
            )
        if cutout:
            mat.update(alphaMode="MASK", alphaCutoff=0.32)
        out.doc["materials"].append(mat)
        return len(out.doc["materials"]) - 1

    silk = material(
        "Kingfisher damask", (0.75, 0.87, 0.82), 0.62, 0.12, "heron-damask.jpg"
    )
    gilt = material("Couched gold", (0.59, 0.35, 0.085), 0.40, 0.68)
    feather = material(
        "Pearl flight feathers", (0.86, 0.90, 0.83), 0.68, 0.02, "heron-quill.png", True
    )
    batches = {}

    def patch(slot, cols, rows, fn):
        p, n, uv, j, w, idx = batches.setdefault(slot, ([], [], [], [], [], []))
        first = len(p)
        for r in range(rows + 1):
            v = r / rows
            for c in range(cols + 1):
                u = c / cols
                pos, tex, skin = fn(u, v)
                p.append(pos)
                uv.append(tex)
                j.append(tuple(([bones[b] for b, _ in skin] + [0] * 4)[:4]))
                w.append(tuple(([weight for _, weight in skin] + [0.0] * 4)[:4]))
                a = fn(min(1, u + 0.001), v)[0]
                b = fn(max(0, u - 0.001), v)[0]
                d = fn(u, min(1, v + 0.001))[0]
                e = fn(u, max(0, v - 0.001))[0]
                n.append(
                    unit(
                        cross(
                            tuple(x - y for x, y in zip(a, b)),
                            tuple(x - y for x, y in zip(d, e)),
                        )
                    )
                )
                if c and r:
                    k = first + r * (cols + 1) + c
                    idx.extend([k - cols - 2, k - cols - 1, k, k - cols - 2, k, k - 1])

    def coat(u, v):
        a = u * tau
        y = 0.27 + 1.23 * v
        flare = max(0, 1 - v / 0.64)
        rib = max(0, (v - 0.62) / 0.38)
        pleat = (0.017 + 0.047 * flare) * cos(14 * a + 0.6 * v)
        x = (0.23 + 0.24 * flare + 0.057 * rib + pleat) * sin(a)
        z = 0.018 + (0.195 + 0.115 * flare + 0.59 * pleat) * cos(a)
        thigh = "thigh_l" if x > 0 else "thigh_r"
        skin = (
            [("pelvis", 1 - flare * 0.62), (thigh, flare * 0.62)]
            if v < 0.64
            else [("pelvis", 1 - rib), ("spine_05", rib)]
        )
        return (x, y - 0.035 * flare * cos(7 * a), z), (u * 3, 1 - v), skin

    patch(silk, 84, 36, coat)
    for band in (0.05, 0.59, 0.64, 0.95):

        def border(u, v):
            (x, y, z), uv, j = coat(u, band + 0.009 * v)
            return (x * 1.014, y, z * 1.014), uv, j

        patch(gilt, 84, 2, border)
    for side, suffix in [(-1, "r"), (1, "l")]:
        chain = ["upperarm_" + suffix, "lowerarm_" + suffix, "hand_" + suffix]

        def sleeve(u, v):
            limb = min(1, int(v * 2))
            t = 2 * v - limb
            a, b = (rest[name] for name in chain[limb : limb + 2])
            x, y, z = [i * (1 - t) + k * t for i, k in zip(a, b)]
            radius = 0.11 + 0.095 * v + 0.017 * sin(u * tau * 8)
            return (
                (
                    x + radius * 0.8 * cos(u * tau),
                    y + side * radius * 0.53 * cos(u * tau),
                    z + radius * sin(u * tau),
                ),
                (u * 1.5, 1 - v),
                [(chain[limb], 1 - t), (chain[limb + 1], t)],
            )

        patch(silk, 32, 16, sleeve)
        for row in range(3):
            for i in range(16 - row):
                t = i / (15 - row)
                start = (
                    side * (0.14 + 0.60 * t),
                    1.42 + 0.52 * t + 0.12 * sin(pi * t),
                    -0.16 - 0.15 * t - row * 0.024,
                )
                length = (0.60 + 0.33 * t) * (1 - 0.27 * row)
                angle = 0.05 + 0.99 * t

                def vane(u, v):
                    width = (u - 0.5) * (0.145 + 0.042 * t)
                    x = start[0] + side * (v * length * sin(angle) + width * cos(angle))
                    y = start[1] - v * length * cos(angle) + width * sin(angle)
                    z = start[2] - 0.19 * v * v + 0.04 * sin(pi * v) - abs(width) * 0.22
                    return (
                        (x, y, z),
                        (u, v),
                        [("spine_05", 0.84), ("clavicle_" + suffix, 0.16)],
                    )

                patch(feather, 4, 9, vane)
    for slot, (p, n, uv, j, w, idx) in batches.items():
        attrs = dict(
            POSITION=out.data(p, "VEC3", bounds=True),
            NORMAL=out.data(n, "VEC3"),
            TEXCOORD_0=out.data(uv, "VEC2"),
            JOINTS_0=out.data(j, "VEC4", 5123),
            WEIGHTS_0=out.data(w, "VEC4"),
        )
        out.doc["meshes"][0]["primitives"].append(
            dict(
                attributes=attrs,
                indices=out.data([(i,) for i in idx], "SCALAR", 5125),
                material=slot,
            )
        )
