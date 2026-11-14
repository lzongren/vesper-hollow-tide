"""Fit the magnolia coat, crisscross sash, coiled hair and mapped portrait to the combat rig."""

import json
from math import atan2, cos, pi, sin, tau

from bind_pilgrim import cross, unit
from garment_surfaces import garment_surfaces


def dress(out, bones, rest, art):
    def material(name, rgb, roughness, metallic=0, texture=None):
        pbr = dict(
            baseColorFactor=[*rgb, 1],
            metallicFactor=metallic,
            roughnessFactor=roughness,
        )
        if texture:
            pbr["baseColorTexture"] = out.image(
                (art / texture).read_bytes(), "image/jpeg", name
            )
        out.doc["materials"].append(
            dict(name=name, doubleSided=True, pbrMetallicRoughness=pbr)
        )
        return len(out.doc["materials"]) - 1

    face = material("WayfarerSkin", (1, 1, 1), 0.60, texture="magnolia-face.jpg")
    silk = material("MagnoliaSilk", (1, 1, 1), 0.66, texture="magnolia-silk.jpg")
    lining = material("CeladonSilk", (1, 1, 1), 0.76, texture="celadon.jpg")
    crimson = material("RoseBinding", (1, 1, 1), 0.71, texture="rosewood.jpg")
    brass = material("ChasedBrass", (1, 1, 1), 0.38, 0.64, "brass.jpg")
    hair = material("InkHair", (1, 1, 1), 0.63, texture="hair.jpg")
    jade = material("CloudJade", (0.16, 0.40, 0.32), 0.27, 0.12)
    pearl = material("SeedPearl", (0.84, 0.75, 0.62), 0.28, 0.09)
    petal = material("MagnoliaJade", (0.55, 0.76, 0.61), 0.34, 0.04)
    river = material("RiverBrocade", (1, 1, 1), 0.65, texture="river-sash.jpg")
    patch, finish = garment_surfaces(out, bones)
    head = [("head", 1)]
    waist = [("pelvis", 1)]

    def smooth(t):
        t = min(1, max(0, t))
        return t * t * (3 - 2 * t)

    def face_uv(x, y):
        # Place the eyeballs and lip seam on the corresponding portrait landmarks.
        v = 0.459 - (y - 7.284) * (0.400 if y < 7.284 else 0.354)
        return (0.511 + 0.389 * x, v)

    # Preserve the open eyelids and lips of the CC0 human mesh. Only the face
    # receives the frontal projection; the back of the skull carries wrapped hair.
    source = json.loads((art / "head.json").read_text())
    verts = source["vertices"]

    def sculpt(x, y, z):
        jaw = min(1, max(0, (7.14 - y) / 0.80))
        return (
            x * (1 - 0.13 * jaw) * (0.78 + 0.22 * smooth((y - 5.76) / 0.30)),
            y - 0.034 * jaw,
            z - 0.054 * jaw * max(0, z - 0.5),
        )

    shaped = [sculpt(*v) for v in verts]
    normals = [[0.0, 0.0, 0.0] for _ in verts]
    batches = {face: [], hair: []}
    for f in source["faces"]:
        a, b, c = (shaped[i] for i in f[:3])
        normal = cross([j - i for i, j in zip(a, b)], [j - i for i, j in zip(a, c)])
        for i in f:
            for k in range(3):
                normals[i][k] += normal[k]
        x, y, z = [sum(verts[i][k] for i in f) / len(f) for k in range(3)]
        # Keep the photographed forehead, with the scalp continuing in one
        # sweep from the temple past the ear to the nape.
        angle = abs(atan2(x, z - 0.55))
        hairline = 8.14 - 0.40 * smooth((angle - 0.50) / 0.57)
        hairline -= 0.59 * smooth((angle - 1.07) / 0.40)
        hairline -= 0.59 * smooth((angle - 1.53) / 0.95)
        slot = hair if y > hairline else face
        for j in range(1, len(f) - 1):
            batches[slot].extend([f[0], f[j], f[j + 1]])

    def pos(x, y, z):
        return (0.104 * x, 1.625 + 0.103 * (y - 7.0), 0.104 * (z - 0.32))

    coords = [pos(*v) for v in shaped]
    uv = []
    neck_weights = []
    for x, y, z in verts:
        u, v = face_uv(x, y)
        portrait = smooth((z - 0.72) / 0.37) * smooth((y - 6.04) / 0.26)
        # The rear neck and ears sample clean skin, away from the portrait edge.
        uv.append((0.62 + (u - 0.62) * portrait, 0.70 + (v - 0.70) * portrait))
        neck = 1 - smooth((y - 5.78) / 0.63)
        neck_weights.append((1 - neck, neck, 0, 0))
    attrs = dict(
        POSITION=out.data(coords, "VEC3", bounds=True),
        NORMAL=out.data([unit(n) for n in normals], "VEC3"),
        TEXCOORD_0=out.data(uv, "VEC2"),
        JOINTS_0=out.data(
            [(bones["head"], bones["neck_01"], 0, 0)] * len(verts), "VEC4", 5123
        ),
        WEIGHTS_0=out.data(neck_weights, "VEC4"),
    )
    for mat, indices in batches.items():
        material_attrs = dict(attrs)
        if mat == hair:
            # Brush the scalp in the direction of the knot instead of projecting
            # the face image over the hairline and rear of the head.
            hair_uv = [
                (atan2(x, z - 0.44) / tau * 5 + 0.5 + 0.26 * (y - 7), (8.5 - y) * 0.65)
                for x, y, z in verts
            ]
            material_attrs["TEXCOORD_0"] = out.data(hair_uv, "VEC2")
        out.doc["meshes"][0]["primitives"].append(
            dict(
                attributes=material_attrs,
                indices=out.data([(i,) for i in indices], "SCALAR", 5125),
                material=mat,
            )
        )

    def globe(mat, centre, radii, skin, texture_eyes=False, grooves=0):
        def surface(u, v):
            a, b = u * tau, (v - 0.5) * pi
            ridges = 1 + 0.06 * cos(27 * a + 8 * b) * grooves
            x = centre[0] + radii[0] * cos(b) * sin(a) * ridges
            y = centre[1] + radii[1] * sin(b)
            z = centre[2] + radii[2] * cos(b) * cos(a) * ridges
            uv = face_uv(x / 0.104, 7 + (y - 1.625) / 0.103) if texture_eyes else (u, v)
            return (x, y, z), uv, skin

        patch(mat, 48, 24, surface)

    for side in (-1, 1):
        globe(
            face, pos(side * 0.308, 7.284, 1.245), (0.0128, 0.0125, 0.0126), head, True
        )
    # A low, offset chignon reads in silhouette in both profile and the combat view.
    globe(hair, (-0.015, 1.734, -0.076), (0.070, 0.061, 0.055), head, grooves=1)

    def strand(mat, path, width, skin, steps=22):
        def surface(u, v):
            p = path(v)
            a, b = path(max(0, v - 0.001)), path(min(1, v + 0.001))
            tangent = unit([j - i for i, j in zip(a, b)])
            up = (0, 1, 0) if abs(tangent[1]) < 0.9 else (1, 0, 0)
            n = unit(cross(tangent, up))
            m = cross(tangent, n)
            w = width(v)
            return (
                tuple(
                    p[i] + w * (n[i] * cos(tau * u) + m[i] * sin(tau * u))
                    for i in range(3)
                ),
                (u, v),
                skin,
            )

        patch(mat, 8, steps, surface)

    # An asymmetric oval follows the cranial vault from the nape to a
    # displaced crown. Both radii vary continuously across the temple.
    def hair_shell(a, v):
        temple = abs(atan2(sin(a), cos(a)))
        edge = 8.045 - 0.39 * smooth((temple - 0.32) / 0.77)
        edge -= 0.44 * smooth((temple - 1.06) / 0.45)
        edge -= 0.53 * smooth((temple - 1.62) / 0.95)
        h = edge + (8.57 - edge) * sin(v * pi / 2)
        t = (h - 7.42) / (1.15 if h >= 7.42 else 1.32)
        radius = max(0, 1 - t * t) ** 0.5
        wave = 0.009 * cos(15 * a + 2.8 * v) * sin(pi * v)
        width = (0.82 + wave) * radius
        depth = (1.03 + wave) * radius
        return pos(width * sin(a), h, 0.56 + depth * cos(a))

    def swept_hair(u, v):
        a = tau * u
        # Offset each upper row towards the coil, visually combing the strands.
        angle = a + 0.26 * sin(a) * sin(pi * v)
        p = hair_shell(angle, v)
        return p, (u * 4 + 0.22 * sin(a) * v, 0.94 - 0.88 * v), head

    patch(hair, 128, 38, swept_hair)
    for side in (-1, 1):
        for j in range(4):
            root = hair_shell(side * (1.03 + 0.055 * j), 0.08)

            def wisp(t):
                return (
                    root[0] + side * (0.009 * sin(pi * t) - 0.003 * t),
                    root[1] - (0.073 + 0.011 * j) * t,
                    root[2] - 0.013 * t + 0.002 * sin(pi * t),
                )

            strand(hair, wisp, lambda t: 0.0012 * (1 - 0.95 * t), head)
    # Coiled lengths traverse the back of the knot in opposite directions.
    for k in range(4):

        def coil(t):
            a = (t * 1.38 + 0.25 * k) * tau
            return (
                -0.013 + (0.050 + 0.013 * t) * cos(a),
                1.744 + 0.039 * sin(a) - 0.022 * t,
                -0.087 - 0.014 * k + 0.009 * sin(2 * a),
            )

        strand(hair, coil, lambda t: 0.013 + 0.003 * sin(pi * t), head, 64)

    # The comb sits above the left ear. Thin cupped petals, stamens and
    # pearl strings cast their own silhouettes instead of being baked onto the hair.
    strand(
        brass,
        lambda t: (-0.087 + 0.199 * t, 1.738 + 0.049 * t, -0.066 + 0.025 * t),
        lambda t: 0.0027 + 0.0012 * t,
        head,
    )
    for size, ox, oy, oz in [
        (1, 0.086, 1.774, -0.034),
        (0.66, 0.055, 1.791, -0.042),
        (0.48, 0.109, 1.755, -0.030),
    ]:
        for j in range(6):
            a = (j / 6 + 0.03) * tau

            def flower(u, v):
                span = 0.011 * size * (0.13 + 0.87 * sin(pi * v) ** 0.72) * (2 * u - 1)
                length = 0.030 * size * v
                return (
                    (
                        ox + length * cos(a) - span * sin(a),
                        oy + length * sin(a) + span * cos(a),
                        oz
                        + 0.010 * size * sin(pi * v)
                        + 0.008 * size * (2 * u - 1) ** 2 * v,
                    ),
                    (u, v),
                    head,
                )

            patch(petal, 8, 12, flower)
        globe(pearl, (ox, oy, oz + 0.008 * size), (0.005 * size,) * 3, head)
    for j in range(3):
        x = 0.090 + 0.009 * j
        length = 0.048 + 0.019 * (j % 2)

        def chain(t):
            return (x + 0.004 * sin(t * pi), 1.756 - length * t, -0.036 + 0.002 * j)

        strand(brass, chain, lambda t: 0.0011, head)
        for t in (0.37, 0.73, 1):
            globe(pearl, chain(t), (0.0034, 0.0048, 0.0034), head)
    for side in (-1, 1):
        globe(pearl, (side * 0.082, 1.628, 0.028), (0.0038, 0.0051, 0.0038), head)

    # The bodice, skirt and lapel share one surface from hem to neckline.
    # Ring radii are half-width and half-depth in the skeleton's rest pose.
    rings = (
        (0.425, 0.281, 0.226),
        (0.67, 0.251, 0.205),
        (0.83, 0.233, 0.198),
        (0.99, 0.177, 0.151),
        (1.09, 0.158, 0.127),
        (1.21, 0.163, 0.123),
        (1.32, 0.179, 0.142),
        (1.385, 0.183, 0.135),
        (1.431, 0.179, 0.108),
        (1.465, 0.146, 0.089),
        (1.488, 0.097, 0.074),
        (1.508, 0.062, 0.064),
    )

    def cloth(a, y, lift=0):
        k = next(
            (i for i in range(len(rings) - 1) if y <= rings[i + 1][0]), len(rings) - 2
        )
        lo, hi = rings[k : k + 2]
        t = (y - lo[0]) / (hi[0] - lo[0])

        # Hermite slopes pass smoothly through each measured section.
        def radius(i):
            prev = rings[max(0, k - 1)]
            after = rings[min(len(rings) - 1, k + 2)]
            dt = hi[0] - lo[0]
            m0 = dt * (hi[i] - prev[i]) / (hi[0] - prev[0])
            m1 = dt * (after[i] - lo[i]) / (after[0] - lo[0])
            return (
                lo[i] * (2 * t**3 - 3 * t * t + 1)
                + hi[i] * (3 * t * t - 2 * t**3)
                + m0 * t * (1 - t) ** 2
                + m1 * t * t * (t - 1)
            )

        flare = 1 - smooth((y - 0.43) / 0.64)
        fold = (0.0025 + 0.015 * flare) * cos(12 * a + 2 * y) + 0.006 * flare * cos(
            7 * a - 3 * y
        )
        x = (radius(1) + fold + lift) * sin(a)
        z = (radius(2) + 0.65 * fold + lift) * cos(a) + 0.010
        depth = 0.025 * smooth((y - 1.43) / 0.078) * max(0, cos(a))
        leg = 0.83 * flare
        rib = smooth((y - 0.99) / 0.19)
        chest = smooth((y - 1.15) / 0.20)
        skin = [
            ("thigh_l" if sin(a) > 0 else "thigh_r", leg),
            ("pelvis", 1 - leg - rib),
            ("spine_02", rib - chest),
            ("spine_05", chest),
        ]
        return (x, y - depth - 0.011 * flare * cos(6 * a), z), skin

    def bodice(u, v):
        a = tau * (u - 0.5)
        p, skin = cloth(a, 0.982 + 0.526 * v)
        return p, (u, 0.94 - 0.87 * v), skin

    def neckband(u, v):
        a = tau * u
        bottom, _ = cloth(a, 1.503)
        # A shallow standing collar covers the open neck boundary while
        # flexing with the first neck joint during turns.
        x = bottom[0] * (1 - v) + 0.057 * sin(a) * v
        z = bottom[2] * (1 - v) + (0.016 + 0.063 * cos(a)) * v
        y = bottom[1] + (1.521 - 0.012 * max(0, cos(a)) - bottom[1]) * v
        w = 0.52 * v
        return (x, y, z), (u, 0.40 + 0.12 * v), [("spine_05", 1 - w), ("neck_01", w)]

    patch(lining, 72, 10, neckband)
    patch(silk, 96, 52, bodice)
    for j in range(8):

        def panel(u, v):
            a = tau * (j + (u - 0.5) * 1.025) / 8
            p, skin = cloth(a, 0.425 + 0.573 * v)
            return p, (0.05 + 0.90 * u, 0.995 - 0.91 * v), skin

        patch(lining if j in (2, 6) else silk, 20, 36, panel)

        def trim(u, v):
            p, tex, skin = panel(0.022 * u, v)
            x, y, z = p
            return (x * 1.007, y, z * 1.008), tex, skin

        patch(brass if j % 2 == 0 else crimson, 2, 36, trim)

    for side, suffix in [(-1, "r"), (1, "l")]:
        chain = [k + "_" + suffix for k in ("upperarm", "lowerarm", "hand")]

        def arm(u, v):
            seg = min(1, int(2 * v))
            t = 2 * v - seg
            a, b = (rest[k] for k in chain[seg : seg + 2])
            axis = unit([j - i for i, j in zip(a, b)])
            n = unit(cross(axis, (0, 0, 1)))
            m = cross(axis, n)
            width = (
                0.071 * (1 - v)
                + 0.043 * v
                + 0.0025 * sin(10 * pi * v + 2 * cos(tau * u))
            )
            p = tuple(
                a[k] * (1 - t)
                + b[k] * t
                + width * (n[k] * cos(tau * u) + m[k] * sin(tau * u))
                for k in range(3)
            )
            return p, (u, 1 - v), [(chain[seg], 1 - t), (chain[seg + 1], t)]

        patch(silk, 36, 32, arm)

        def sleeve_cap(u, v):
            ring, _, _ = arm(u, 0)
            centre = rest[chain[0]]
            angle = v * pi / 2
            # The shoulder dome extends out of the sleeve opening along the
            # upper-arm axis, then joins the sloping bodice close to the neck.
            axis = unit([a - b for a, b in zip(centre, rest[chain[1]])])
            dome = 0.048 * sin(angle)
            p = tuple(
                centre[k] + (ring[k] - centre[k]) * cos(angle) + axis[k] * dome
                for k in range(3)
            )
            blend = 0.60 * smooth(v)
            return p, (u, 0.06 + 0.22 * v), [(chain[0], 1 - blend), ("spine_05", blend)]

        patch(silk, 36, 16, sleeve_cap)

        for band in (0.11, 0.17, 0.67, 0.73, 0.82, 0.88, 0.94):

            def cuff(u, v):
                p, uv, skin = arm(u, band + 0.022 * v)
                a = tau * u
                return (p[0] + 0.002 * cos(a), p[1] + 0.002 * sin(a), p[2]), uv, skin

            patch(brass if band in (0.17, 0.67, 0.94) else crimson, 36, 3, cuff)

        def collar(u, v):
            end = 1.34 if side < 0 else 1.045
            y = 1.508 + (end - 1.508) * v
            drop = (1.508 - y) / 0.463
            a = side * (0.93 - 2.02 * drop**0.73)
            span = 0.39 - 0.15 * smooth(drop * 2)
            a += (u - 0.5) * span
            p, skin = cloth(a, y, 0.0035 if side < 0 else 0.0055)
            return p, (0.12 + 0.20 * u, 0.92 * v), skin

        patch(lining, 10, 52, collar)
        for edge in (0, 0.935):

            def braid(u, v):
                (x, y, z), uv, skin = collar(edge + 0.065 * u, v)
                return (x * 1.007, y + 0.0004, z + 0.0011), uv, skin

            patch(brass, 2, 52, braid)

    def belt(u, v):
        a = tau * u
        return (
            (
                0.178 * sin(a),
                1.01 + 0.094 * v + 0.007 * sin(a * 3),
                0.160 * cos(a) + 0.015,
            ),
            (u, v),
            waist,
        )

    patch(crimson, 72, 8, belt)
    for band in (0.05, 0.88):
        patch(brass, 72, 2, lambda u, v: belt(u, band + 0.045 * v))
    globe(jade, (0.025, 1.065, 0.182), (0.036, 0.024, 0.011), waist)
    # Two folded loops gather the streamers against the rear waistband.
    for side in (-1, 1):

        def loop(u, v):
            a = tau * v
            width = 0.018 * (2 * u - 1)
            return (
                (
                    side * (0.018 + 0.075 * (1 - cos(a)) / 2) + width * sin(a),
                    1.066 + 0.024 * sin(a) + width * cos(a),
                    -0.157 - 0.025 * sin(pi * v) - 0.008 * cos(tau * u),
                ),
                (u, v),
                waist,
            )

        patch(lining, 12, 40, loop)

        def streamer(u, v):
            # Each warp row has a slightly different roll and a forked hem.
            # UV V is also the lever arm for motion, zero at the fastening.
            length = 0.54 if side > 0 else 0.44
            roll = side * (0.18 + 0.70 * v + 0.27 * sin(5 * v))
            half_width = 0.023 + 0.017 * sin(pi * v * 0.86)
            crosswise = (2 * u - 1) * half_width
            spread = 0.033 + 0.068 * sin(pi * v * 0.65)
            x = side * spread + crosswise * cos(roll)
            z = -0.164 - 0.096 * v + 0.012 * sin(5 * v) + crosswise * sin(roll)
            y = 1.062 - length * v + 0.022 * (1 - abs(2 * u - 1)) * v**12
            return (x, y, z), (u, v), waist

        patch(river, 16, 48, streamer)
    globe(jade, (0, 1.064, -0.175), (0.020, 0.019, 0.012), waist)
    finish()
