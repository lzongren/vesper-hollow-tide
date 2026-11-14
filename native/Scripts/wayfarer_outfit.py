"""Fit the magnolia coat, crisscross sash, coiled hair and mapped portrait to the combat rig."""

import json
from math import atan2, cos, exp, pi, sin, tau

from bind_pilgrim import cross, unit
from garment_surfaces import garment_surfaces
from cloud_collar import cloud_collar
from plum_hairpin import butterfly
from wayfarer_blink import install_shape
from scalp_fit import scalp_radius


def dress(out, bones, rest, art):
    def material(name, rgb, roughness, metallic=0, texture=None):
        pbr = dict(
            baseColorFactor=[*rgb, 1],
            metallicFactor=metallic,
            roughnessFactor=roughness,
        )
        if texture:
            pbr["baseColorTexture"] = out.image(
                (art / texture).read_bytes(),
                "image/png" if texture.endswith(".png") else "image/jpeg",
                name,
            )
        out.doc["materials"].append(
            dict(name=name, doubleSided=True, pbrMetallicRoughness=pbr)
        )
        return len(out.doc["materials"]) - 1

    face = material("WayfarerSkin", (1, 1, 1), 0.60, texture="plum-face.jpg")
    silk = material("MagnoliaSilk", (1, 1, 1), 0.66, texture="magnolia-silk.jpg")
    lining = material("CeladonSilk", (1, 1, 1), 0.76, texture="celadon.jpg")
    crimson = material("RoseBinding", (1, 1, 1), 0.71, texture="rosewood.jpg")
    brass = material("ChasedBrass", (1, 1, 1), 0.38, 0.64, "brass.jpg")
    hair = material("InkHair", (1, 1, 1), 0.63, texture="hair.jpg")
    jade = material("CloudJade", (0.16, 0.40, 0.32), 0.27, 0.12)
    pearl = material("SeedPearl", (0.84, 0.75, 0.62), 0.28, 0.09)
    enamel = material("KingfisherEnamel", (0.048, 0.34, 0.36), 0.24, 0.26)
    fringe = material("TempleStrands", (1, 1, 1), 0.64, texture="temple-strands.png")
    out.doc["materials"][fringe].update(alphaMode="MASK", alphaCutoff=0.38)
    river = material("RiverBrocade", (1, 1, 1), 0.65, texture="river-sash.jpg")
    brocade = material("RuyiBrocade", (1, 1, 1), 0.58, texture="ruyi-embroidery.jpg")
    eye = material("WetIris", (1, 1, 1), 0.23, texture="ruyi-face.jpg")
    patch, finish = garment_surfaces(out, bones)
    head = [("head", 1)]
    waist = [("pelvis", 1)]

    def smooth(t):
        t = min(1, max(0, t))
        return t * t * (3 - 2 * t)

    def face_uv(x, y):
        # Place the eyeballs and lip seam on the corresponding portrait landmarks.
        v = 0.454 - (y - 7.284) * (0.435 if y < 7.284 else 0.342)
        return (0.508 + 0.416 * x, v)

    # Preserve the open eyelids and lips of the CC0 human mesh. Only the face
    # receives the frontal projection; the back of the skull carries wrapped hair.
    source = json.loads((art / "head.json").read_text())
    verts = source["vertices"]

    def sculpt(x, y, z):
        jaw = min(1, max(0, (7.14 - y) / 0.80))
        # Lift the malar pads and round the transition into the jaw while
        # retaining the rig's eyelid and mouth boundaries.
        cheek = exp(-(((abs(x) - 0.42) / 0.26) ** 2) - ((y - 7.01) / 0.24) ** 2)
        front = smooth((z - 0.80) / 0.44)
        nose = exp(-((x / 0.18) ** 2) - ((y - 6.95) / 0.29) ** 2)
        return (
            x
            * (1 + 0.035 * cheek * front - 0.15 * jaw)
            * (0.78 + 0.22 * smooth((y - 5.76) / 0.30)),
            y + 0.050 * jaw * front + 0.018 * cheek * front,
            z + front * (0.061 * cheek - 0.072 * nose) - 0.032 * jaw * max(0, z - 0.5),
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
        slot = hair if y > hairline - 0.20 * smooth((angle - 0.65) / 0.45) else face
        for j in range(1, len(f) - 1):
            batches[slot].extend([f[0], f[j], f[j + 1]])

    def pos(x, y, z):
        return (0.104 * x, 1.625 + 0.103 * (y - 7.0), 0.104 * (z - 0.32))

    coords = [pos(*v) for v in shaped]
    uv = []
    coverage = []
    neck_weights = []
    for x, y, z in verts:
        u, v = face_uv(x, y)
        # Keep the projected features straight. The skin shader fades their
        # colour into a cheek swatch at the temples, ears and under the jaw.
        uv.append((min(0.99, max(0.01, u)), min(0.99, max(0.01, v))))
        front = smooth((z - 0.77) / 0.42) * smooth((y - 6.04) / 0.26)
        side = smooth((abs(x) - 0.53) / 0.20) * (1 - smooth((z - 1.02) / 0.28))
        coverage.append((front * (1 - side), 0))
        neck = 1 - smooth((y - 5.78) / 0.63)
        neck_weights.append((1 - neck, neck, 0, 0))
    attrs = dict(
        POSITION=out.data(coords, "VEC3", bounds=True),
        NORMAL=out.data([unit(n) for n in normals], "VEC3"),
        TEXCOORD_0=out.data(uv, "VEC2"),
        TEXCOORD_1=out.data(coverage, "VEC2"),
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
            eye, pos(side * 0.308, 7.284, 1.245), (0.0128, 0.0125, 0.0126), head, True
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
    scalp = scalp_radius(shaped, source["faces"])

    def hair_shell(a, v):
        temple = abs(atan2(sin(a), cos(a)))
        edge = 8.045 - 0.39 * smooth((temple - 0.32) / 0.77)
        edge -= 0.44 * smooth((temple - 1.06) / 0.45)
        edge -= 0.53 * smooth((temple - 1.62) / 0.95)
        # The part sits above the left brow. The opposite wave hangs lower.
        edge += 0.13 * sin(a + 0.35) * max(0, cos(a)) - 0.05 * cos(3 * a)
        h = edge + (8.57 - edge) * sin(v * pi / 2)
        t = (h - 7.42) / (1.15 if h >= 7.42 else 1.32)
        radius = max(0, 1 - t * t) ** 0.5
        wave = 0.009 * cos(15 * a + 2.8 * v) * sin(pi * v)
        width = (0.87 + wave) * radius
        depth = (1.08 + wave) * radius
        x, z = width * sin(a), depth * cos(a)
        length = (x * x + z * z) ** 0.5
        # Touch the forehead at the roots; let the bun retain its dressed volume.
        weight = (1 - smooth((v - 0.04) / 0.40)) * (1 - smooth((temple - 1.23) / 0.34))
        if weight > 0 and length > 0:
            surface = scalp(atan2(x, z), h, length)
            fitted = surface + 0.016 + 0.045 * smooth((v - 0.02) / 0.38)
            scale = 1 + weight * (fitted / length - 1)
            x, z = x * scale, z * scale
        return pos(x, h, 0.56 + z)

    def swept_hair(u, v):
        a = tau * u
        # Offset each upper row towards the coil, visually combing the strands.
        angle = a + 0.26 * sin(a) * sin(pi * v)
        p = hair_shell(angle, v)
        return p, (u * 4 + 0.22 * sin(a) * v, 0.94 - 0.88 * v), head

    patch(hair, 128, 38, swept_hair)
    # Broad overlapping locks sweep from the offset part across each temple.
    # The ridge fades into the cap at both ends rather than forming a tube.
    for side in (-1, 1):
        for layer in range(3):

            def lock(u, v, side=side, layer=layer):
                sweep = v * v * (3 - 2 * v)
                angle = 0.22 + side * (0.035 * layer + (1.32 + 0.10 * layer) * sweep)
                width = (0.07 + 0.13 * sin(pi * v)) * (1 - 0.83 * v**4)
                angle += (2 * u - 1) * width
                row = 0.47 + 0.103 * layer - (0.47 + 0.100 * layer) * v
                x, y, z = hair_shell(angle, row)
                crest = (0.0007 + 0.0021 * sin(pi * u)) * sin(pi * v) ** 0.65
                drop = (0.007 + 0.0013 * layer) * v**4
                return (
                    (x + crest * sin(angle), y - drop, z + crest * cos(angle)),
                    (u * 0.36, v),
                    head,
                )

            patch(hair, 10, 38, lock)
    # Lace the solid cap into the photographed forehead with two feathered
    # temple panels. The UVs run from the roots down to the tapered ends.
    for side in (-1, 1):

        def temple(u, v, side=side):
            angle = 0.13 + side * (1.56 * u + 0.078 * v * (0.16 + 0.84 * u))
            x, y, z = hair_shell(angle, 0.12 * (1 - v) ** 2)
            offset = 0.00038 + 0.00046 * sin(pi * v)
            drop = (0.0018 + 0.0060 * u) * (0.22 + 0.78 * smooth(u / 0.22)) * v**1.4
            return (
                (x + offset * sin(angle), y - drop, z + offset * cos(angle)),
                (u * 3.0, v),
                head,
            )

        patch(fringe, 74, 12, temple)
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

    # The openwork butterfly sits above the left ear on a pin through the coil.
    strand(
        brass,
        lambda t: (-0.087 + 0.187 * t, 1.738 + 0.039 * t, -0.066 + 0.018 * t),
        lambda t: 0.0027 + 0.0012 * t,
        head,
    )
    butterfly(patch, strand, globe, brass, enamel, pearl, head)
    for j in range(3):
        x = 0.089 + 0.0075 * j
        length = 0.048 + 0.019 * (j % 2)

        def chain(t):
            return (x + 0.004 * sin(t * pi), 1.755 - length * t, -0.036 + 0.002 * j)

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
                (0.055 + 0.016 * smooth(v / 0.23)) * (1 - v)
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
            dome = 0.016 * sin(angle)
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
    cloud_collar(patch, brocade, brass, crimson)
    finish()
    install_shape(out, face, verts)
