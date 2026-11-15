"""Fit the magnolia coat, crisscross sash, coiled hair and mapped portrait to the combat rig."""

from digital_head import add_head, skin_reflectance
from bisect import bisect_right
from math import atan2, cos, exp, pi, sin, tau

from bind_pilgrim import cross, unit
from garment_surfaces import garment_surfaces
from spectre_regalia import regalia, shoulder_silks
from jade_coiffure import coiffure
from begonia_ribbons import knot
from wayfarer_legs import riding_legs
from camellia_jewels import pendants
from scalp_fit import fit_hair_margin, scalp_radius


def dress(out, bones, rest, art):
    cache = art.parents[1] / "Saved" / "DigitalHuman"

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

    face = material(
        "WayfarerSkin", (1, 1, 1), 0.60, texture=str(cache / "HaitangDiffuse.jpg")
    )
    silk = material("SpectreIvory", (1, 1, 1), 0.58, texture="spectre-silk.jpg")
    lining = material(
        "MourningSage", (0.48, 0.62, 0.52), 0.7, texture="spectre-silk.jpg"
    )
    crimson = material("RoseBinding", (1, 1, 1), 0.71, texture="rosewood.jpg")
    brass = material("ChasedBrass", (1, 1, 1), 0.38, 0.64, "brass.jpg")
    hair = material("InkHair", (1, 1, 1), 0.63, texture="hair.jpg")
    jade = material("CloudJade", (0.16, 0.40, 0.32), 0.27, 0.12)
    pearl = material("SeedPearl", (0.84, 0.75, 0.62), 0.28, 0.09)
    flower = material("WhiteJadePetal", (0.80, 0.85, 0.69), 0.30, 0.04)
    locks = material("WillowLocks", (1, 1, 1), 0.49, texture="willow-locks.png")
    out.doc["materials"][locks].update(alphaMode="MASK", alphaCutoff=0.38)
    temple_hair = material(
        "TempleSilkHair", (1, 1, 1), 0.74, texture="temple-fibers.png"
    )
    out.doc["materials"][temple_hair].update(alphaMode="BLEND")
    fringe = material("TempleStrands", (1, 1, 1), 0.64, texture="camellia-hairline.png")
    out.doc["materials"][fringe].update(alphaMode="MASK", alphaCutoff=0.38)
    river = material("RiverBrocade", (1, 1, 1), 0.65, texture="river-sash.jpg")
    silver = material("AntiqueSilver", (0.61, 0.58, 0.46), 0.37, 0.80)
    bare = material(
        "NecklineSkin", (1, 1, 1), 0.60, texture=str(cache / "HaitangDiffuse.jpg")
    )
    ribbon = material("BegoniaRibbon", (1, 1, 1), 0.46, texture="begonia-ribbon.jpg")
    eye = material("WetIris", (1, 1, 1), 0.23, texture=str(cache / "HaitangEye.jpg"))
    lash = material(
        "LashFringe", (1, 1, 1), 0.62, texture=str(cache / "HaitangLashes.png")
    )
    out.doc["materials"][lash].update(alphaMode="MASK", alphaCutoff=0.32)
    teeth = material(
        "PorcelainTeeth", (1, 1, 1), 0.34, texture=str(cache / "HaitangTeeth.jpg")
    )
    ducts = material("TearDuct", (0.41, 0.18, 0.17), 0.25)
    trousers = material("IndigoTwill", (0.14, 0.20, 0.24), 0.81, texture="celadon.jpg")
    boots = material(
        "LinenGaiters", (0.64, 0.67, 0.61), 0.70, texture="spectre-silk.jpg"
    )
    damask = material("LakeSilk", (0.31, 0.41, 0.42), 0.67, texture="celadon.jpg")
    sole = material("BootSole", (0.024, 0.018, 0.019), 0.76)
    patch, finish = garment_surfaces(out, bones)
    head = [("head", 1)]

    def smooth(t):
        t = min(1, max(0, t))
        return t * t * (3 - 2 * t)

    def pos(x, y, z):
        return (0.104 * x, 1.625 + 0.103 * (y - 7), 0.104 * (z - 0.32))

    shaped, faces, neck_ring, finish_shapes = add_head(
        out,
        bones,
        cache,
        dict(
            head=face,
            eyeLeft=eye,
            eyeRight=eye,
            eyelashes=lash,
            teeth=teeth,
            cartilage=ducts,
        ),
    )

    def globe(mat, centre, radii, skin, grooves=0):
        def surface(u, v):
            a, b = u * tau, (v - 0.5) * pi
            ridges = 1 + 0.06 * cos(27 * a + 8 * b) * grooves
            x = centre[0] + radii[0] * cos(b) * sin(a) * ridges
            y = centre[1] + radii[1] * sin(b)
            z = centre[2] + radii[2] * cos(b) * cos(a) * ridges
            return (x, y, z), (u, v), skin

        patch(mat, 48, 24, surface)

    # Close the back and sides of the oral cavity behind the dental arch.
    # The visible opening follows the animated lips and jaw in front of it.
    mucosa = material("OralMucosa", (0.041, 0.008, 0.011), 0.84)

    def inner_cheek(u, v):
        side = 2 * u - 1
        half_height = 0.016 - 0.006 * side**2
        pos = (side * 0.023, 1.584 + (2 * v - 1) * half_height, 0.059 + 0.013 * side**2)
        return pos, (u, v), head

    patch(mucosa, 16, 4, inner_cheek)

    # A low, offset chignon reads in silhouette in both profile and the combat view.
    globe(hair, (-0.021, 1.701, -0.079), (0.061, 0.048, 0.060), head, grooves=1)

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
    scalp = scalp_radius(shaped, faces)

    def hair_shell(a, v):
        temple = abs(atan2(sin(a), cos(a)))
        edge = 7.90 - 0.39 * smooth((temple - 0.32) / 0.77)
        edge -= 0.44 * smooth((temple - 1.06) / 0.45)
        edge -= 0.53 * smooth((temple - 1.62) / 0.95)
        # The part sits above the left brow. The opposite wave hangs lower.
        edge += 0.075 * sin(a + 0.16) * max(0, cos(a)) - 0.062 * cos(2 * a + 0.32)
        edge -= 0.080 * exp(-(((temple - 0.59) / 0.36) ** 2))
        h = edge + (8.48 - edge) * sin(v * pi / 2)
        t = (h - 7.42) / (1.06 if h >= 7.42 else 1.32)
        radius = max(0, 1 - t * t) ** 0.5
        wave = 0.009 * cos(15 * a + 2.8 * v) * sin(pi * v)
        width = (0.87 + wave) * radius
        depth = (1.08 + wave) * radius
        x, z = width * sin(a), depth * cos(a)
        length = (x * x + z * z) ** 0.5
        # Touch the forehead at the roots; let the bun retain its dressed volume.
        weight = (1 - smooth((v - 0.04) / 0.40)) * (1 - smooth((temple - 1.76) / 0.44))
        # At the back of the ear seat only the root of the cap on the skull.
        occipital = smooth((temple - 1.80) / 0.26) * (
            1 - smooth((temple - 2.80) / 0.30)
        )
        weight = max(weight, occipital * (1 - smooth((v - 0.025) / 0.20)))
        if weight > 0 and length > 0:
            surface = scalp(atan2(x, z), h, length)
            sidewall = exp(-(((temple - 1.56) / 0.50) ** 4))
            fitted = (
                surface
                + 0.033
                - 0.029 * max(sidewall, occipital)
                + 0.045 * smooth((v - 0.02) / 0.38)
            )
            scale = 1 + weight * (fitted / length - 1)
            x, z = x * scale, z * scale
        return pos(x, h, 0.56 + z)

    def hair_flow(a, v):
        # Strands sweep away from the curved part towards the knot.
        part = 0.30 + 0.19 * v
        return a + 0.78 * sin(a - part) * sin(pi * v * 0.82)

    def hair_edge(a):
        # In front, the opaque shell stops above the roots. At the nape the
        # overlapping back locks cover the smaller transition.
        temple = abs(atan2(sin(a), cos(a)))
        return (
            0.034
            # Recede behind the helix in shallow, unequal sweeps.
            + exp(-(((temple - 2.18) / 0.37) ** 4)) * (0.018 + 0.004 * sin(9 * a + 0.5))
            + 0.041 * max(0, cos(a))
            + 0.11 * exp(-(((temple - 1.57) / 0.44) ** 4))
        )

    def above_helix(a):
        # Reserve a narrow band on the scalp above the projecting ear.
        # At the lower edge only the wisps extend past the old silhouette.
        azimuth = abs(atan2(sin(a), cos(a)))
        return smooth((azimuth - 1.25) / 0.15) * (1 - smooth((azimuth - 1.80) / 0.16))

    def edge_row(a):
        return hair_edge(a) + 0.046 * above_helix(a)

    combed = fit_hair_margin(
        lambda a, row: hair_shell(hair_flow(a, row), row), edge_row
    )

    def swept_hair(u, v):
        a = tau * u
        edge = edge_row(a)
        row = edge + (1 - edge) * v
        p = combed(a, row)
        return p, (u * 5, 0.96 - 0.92 * row), head

    def roots(u, v):
        a = tau * u
        # The ear projects beyond the scalp. A long wrapping root sheet would
        # intersect the helix and paint through the concha from a side view.
        azimuth = abs(atan2(sin(a), cos(a)))
        pinna = smooth((azimuth - 1.12) / 0.24) * (1 - smooth((azimuth - 2.27) / 0.32))
        row = hair_edge(a) * (1.05 - (1.47 - 1.39 * pinna) * v)
        # Extend the dense-to-sparse root veil behind the projecting ear.
        nape = smooth((azimuth - 1.76) / 0.18) * (1 - smooth((azimuth - 2.85) / 0.21))
        row -= 0.062 * nape * v
        row += 0.046 * above_helix(a) * (1 - v)
        angle = hair_flow(a, row)
        x, y, z = combed(a, row)
        return (x + 0.00018 * sin(angle), y, z + 0.00018 * cos(angle)), (u * 8, v), head

    patch(hair, 144, 38, swept_hair)
    patch(fringe, 160, 16, roots)

    # Lay short swept fibers across the sidewall in staggered rows. The
    # overlap covers the opaque cap edge and thins towards the ear.
    for side in (-1, 1):
        for row in range(2):
            for clump in range(18):
                start_angle = 0.86 + 0.043 * clump + 0.021 * row
                reach = 0.075 + 0.035 * (1 + sin(clump * 2.39 + row))

                def down(u, v):
                    angle = side * (
                        start_angle + 0.085 * v + (u - 0.5) * (0.080 - 0.055 * v)
                    )
                    level = hair_edge(angle) * (1.1 - 0.31 * row) - reach * v
                    x, y, z = hair_shell(angle, level)
                    lift = 0.00042 + 0.00027 * row
                    return (
                        (x + lift * sin(angle), y, z + lift * cos(angle)),
                        ((clump % 4 + u) / 4, v),
                        head,
                    )

                patch(temple_hair, 4, 13, down)

    # Fine upper roots bridge to the denser growth behind the ear. Seat
    # each root in the same combed coordinates as the opaque shell.
    for side in (-1, 1):
        for tuft in range(19):
            phase = tuft * 2.399 + side
            root = 1.31 + 0.029 * tuft + 0.007 * sin(phase)
            length = (0.039 + 0.008 * sin(phase + 0.5)) * (
                1 - 0.28 * smooth((root - 1.60) / 0.24)
            )

            def helix_wisp(u, v):
                a = side * (root + 0.035 * v + (u - 0.5) * (0.055 - 0.032 * v))
                level = hair_edge(a) + 0.045 * above_helix(a) + 0.006 - length * v
                angle = hair_flow(a, level)
                x, y, z = combed(a, level)
                lift = 0.00055
                return (
                    (x + lift * sin(angle), y, z + lift * cos(angle)),
                    ((tuft % 4 + u) / 4, v),
                    head,
                )

            patch(temple_hair, 4, 12, helix_wisp)

    # Down behind the helix runs back toward the nape. Overlap two
    # uneven rows of tapered roots, leaving the projecting ear exposed.
    for side in (-1, 1):
        for row in range(2):
            for tuft in range(17):
                phase = 2.399 * tuft + 0.7 * side + 1.4 * row
                root = 1.83 + 0.046 * tuft + 0.018 * sin(phase)
                reach = (0.050 + 0.014 * sin(phase + 1.3) + 0.008 * row) * (
                    1 - 0.26 * smooth((root - 1.98) / 0.61)
                )

                def ear_down(u, v):
                    sweep = root + (0.074 + 0.030 * sin(phase)) * v
                    angle = side * (sweep + (u - 0.5) * (0.049 - 0.043 * v))
                    level = (
                        hair_edge(angle)
                        + 0.046 * above_helix(angle)
                        + 0.021
                        - 0.005 * row
                        - reach * v
                    )
                    x, y, z = combed(angle, level)
                    angle = hair_flow(angle, level)
                    lift = 0.00048 + 0.00030 * row + 0.00022 * sin(pi * v)
                    return (
                        (x + lift * sin(angle), y, z + lift * cos(angle)),
                        ((tuft % 4 + u) / 4, v),
                        head,
                    )

                patch(temple_hair, 5, 15, ear_down)

    # The front sections are combed sideways from an off-centre part. Each
    # overlapping card has its own arched root and hair-thread alpha fringe.
    for side, count in ((-1, 7), (1, 5)):
        for j in range(count):

            def temple_lock(u, v, j=j, side=side):
                angle = 0.17 + side * (0.08 + 0.065 * j + (0.75 + 0.05 * j) * v)
                row = 0.17 + 0.020 * j - (0.23 + 0.016 * j) * v + 0.032 * sin(pi * v)
                # Taper the card as its tip crosses the roots on the temple.
                width = (0.008 + 0.012 * sin(pi * v)) * (1 - 0.80 * v**3)
                row += (2 * u - 1) * width
                x, y, z = hair_shell(angle, row)
                lift = 0.0003 + 0.0007 * sin(pi * v) + 0.00008 * j
                return (
                    (x + lift * sin(angle), y, z + lift * cos(angle)),
                    ((j % 4 + 0.001 + u * 0.998) / 4, v),
                    head,
                )

            patch(temple_hair, 6, 32, temple_lock)
    # Wispy S-shaped locks break the straight hairline and frame the cheek.
    for side in (-1, 1):
        for j in range(4):

            def face_lock(u, v):
                a = side * (0.47 + 0.055 * j + 0.45 * v + 0.13 * sin(pi * v))
                x, y, z = hair_shell(a, 0.095 - 0.14 * v)
                taper = (1 - v**2) * (0.0033 + 0.0016 * sin(pi * v))
                across = (u - 0.5) * 2 * taper
                return (
                    (
                        x + side * (0.003 + across),
                        y - (0.028 + 0.009 * j) * v * v,
                        z + 0.006 + 0.006 * sin(pi * v) - side * across,
                    ),
                    ((j + u) / 4, v),
                    head,
                )

            patch(temple_hair, 5, 36, face_lock)
    for side in (-1, 1):
        for j in range(9):
            root = hair_shell(side * (1.09 + 0.023 * j), 0.08)

            def wisp(t):
                return (
                    root[0] + side * (0.004 * sin(pi * t + 0.24 * j) - 0.001 * t),
                    root[1] - (0.022 + 0.005 * ((j * 5) % 9)) * t,
                    root[2] - (0.014 + 0.0013 * j) * t + 0.003 * sin(pi * t),
                )

            strand(hair, wisp, lambda t: 0.00020 * (1 - 0.96 * t), head)
    # Coiled lengths traverse the back of the knot in opposite directions.
    for k in range(4):

        def coil(t):
            a = (t * 1.38 + 0.25 * k) * tau
            return (
                -0.020 + (0.045 + 0.012 * t) * cos(a),
                1.713 + 0.032 * sin(a) - 0.022 * t,
                -0.091 - 0.012 * k + 0.009 * sin(2 * a),
            )

        strand(hair, coil, lambda t: 0.013 + 0.003 * sin(pi * t), head, 64)

    coiffure(patch, strand, globe, hair_shell, locks, temple_hair, flower, pearl, brass)
    knot(patch, globe, strand, ribbon, brass, pearl)
    pendants(strand, globe, jade, pearl, brass)

    # The bodice, skirt and lapel share one surface from hem to neckline.
    # Ring radii are half-width and half-depth in the skeleton's rest pose.
    rings = (
        (0.425, 0.260, 0.188),
        (0.58, 0.240, 0.171),
        (0.70, 0.218, 0.153),
        (0.825, 0.201, 0.149),
        (0.92, 0.198, 0.147),
        (0.99, 0.180, 0.131),
        (1.045, 0.151, 0.115),
        (1.105, 0.129, 0.100),
        (1.163, 0.137, 0.106),
        (1.226, 0.154, 0.117),
        (1.285, 0.169, 0.126),
        (1.343, 0.173, 0.133),
        (1.396, 0.166, 0.112),
        (1.438, 0.158, 0.092),
        (1.472, 0.127, 0.077),
        (1.492, 0.085, 0.065),
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
        # The jacket is cut over the ribcage and seat. Build the front and
        # back independently so the form also reads when seen in profile.
        breast = exp(-(((y - 1.31) / 0.083) ** 2) - ((abs(x) - 0.085) / 0.070) ** 2)
        seat = exp(-(((y - 0.912) / 0.103) ** 2))
        # Give the vent clearance over the advancing quadriceps.
        allowance = exp(-(((y - 0.777) / 0.12) ** 2)) * abs(sin(a)) ** 1.5
        x += 0.022 * allowance * sin(a)
        z += 0.030 * allowance * cos(a)
        z += 0.035 * breast * max(0, cos(a)) ** 1.5
        z -= 0.022 * seat * max(0, -cos(a)) ** 2
        depth = 0.025 * smooth((y - 1.43) / 0.078) * max(0, cos(a))
        # The wrap crosses the outer thigh as the hip turns. Follow that
        # joint through the short side vent so the leg stays inside the coat.
        side_panel = smooth((abs(sin(a)) - 0.20) / 0.62)
        leg = max(0.83 * flare, side_panel * smooth((1.045 - y) / 0.18))
        rib = smooth((y - 0.99) / 0.19)
        chest = smooth((y - 1.15) / 0.20)
        skin = [
            ("thigh_l" if sin(a) > 0 else "thigh_r", leg),
            ("pelvis", 1 - leg - rib),
            ("spine_02", rib - chest),
            ("spine_05", chest),
        ]
        return (x, y - depth - 0.011 * flare * cos(6 * a), z), skin

    def opening(a):
        return 1.466 - 0.129 * max(0, cos(a)) ** 2.5 - 0.024 * max(0, -cos(a)) ** 2

    def bodice(u, v):
        a = tau * (u - 0.5)
        p, skin = cloth(a, 0.982 + (opening(a) - 0.982) * v)
        return p, (u, 0.94 - 0.87 * v), skin

    ring = list(range(len(neck_ring)))

    def angle(i):
        return i * tau / len(neck_ring)

    def decolletage(u, v):
        at = u * len(ring)
        k = int(at)
        left, right = ring[k % len(ring)], ring[(k + 1) % len(ring)]
        t = at - k
        a = angle(left) + ((angle(right) - angle(left)) % tau) * t
        neck = tuple(x + (y - x) * t for x, y in zip(neck_ring[left], neck_ring[right]))
        outside, body_weights = cloth(a, opening(a))
        # The upper third follows the throat before broadening over the
        # collarbones. A slight ridge follows each clavicle across the chest.
        expand = v**1.50
        x = neck[0] + (outside[0] - neck[0]) * expand
        z = neck[2] + (outside[2] - neck[2]) * expand
        y = neck[1] + (outside[1] - neck[1]) * v
        ridge = 0.0045 * sin(pi * v) ** 2 * max(0, cos(a)) * sin(a) ** 2
        z += ridge
        h = (neck[1] - 1.512) / 0.045
        blend = smooth(v)
        w = [("head", h * (1 - blend)), ("neck_01", (1 - h) * (1 - blend))]
        w += [(bone, value * blend) for bone, value in body_weights if value > 0]
        return (x, y, z), (0.65 + 0.008 * sin(a) * v, 0.64 + 0.008 * v), w

    # Wind the torso skin outward like the head. Both lip and face then
    # receive lighting with the same front-face orientation.
    patch(bare, len(ring), 30, lambda u, v: decolletage(1 - u, v))
    ring_angles = [angle(i) for i in ring]

    def lapel_surface(a, y, lift):
        if y <= opening(a):
            return cloth(a, y, lift)
        # Trace the same neck panel used by the skin instead of extending
        # the old jacket's smaller top rings across the open neckline.
        az = a % tau
        k = (bisect_right(ring_angles, az) - 1) % len(ring)
        fraction = ((az - ring_angles[k]) % tau) / (
            (ring_angles[(k + 1) % len(ring)] - ring_angles[k]) % tau
        )
        u = (k + fraction) / len(ring)
        top = decolletage(u, 0)[0][1]
        bottom = decolletage(u, 1)[0][1]
        v = max(0, min(1, (top - y) / (top - bottom)))
        (x, h, z), _, weights = decolletage(u, v)
        return (x + lift * sin(a), h + lift * 0.36, z + lift * cos(a)), weights

    patch(silk, 96, 52, bodice)

    # Trousers join inside the waistband, beneath the flared riding panels.
    def yoke(u, v):
        p, skin = cloth(tau * u, 0.81 + 0.205 * v, -0.015)
        return p, (u, v), skin

    patch(trousers, 80, 18, yoke)

    # Side gores run from hip to armscye. Each seam follows the ribcage and
    # turns towards the back under the arm as the player raises her sword.
    for side in (-1, 1):

        def gore(u, v, lift=0.003):
            y = 0.997 + 0.398 * v
            mid = side * (1.44 + 0.18 * v - 0.11 * sin(pi * v))
            width = 0.45 + 0.22 * sin(pi * v) - 0.18 * v
            a = mid + (u - 0.5) * width * 2
            p, skin = cloth(a, y, lift)
            return p, (u, v), skin

        patch(damask, 20, 36, gore)
        for edge in (0.016, 0.965):
            patch(brass, 2, 30, lambda u, v: gore(edge + 0.010 * u, v, 0.0046))

    def hem(a):
        # Shorter inside front panels clear the advancing knee, longer back
        # panels hang behind the calf. The sword-side vent rides highest.
        return (
            0.424
            + 0.173 * max(0, cos(a))
            + 0.116 * sin(a) ** 2
            + 0.092 * max(0, sin(a)) ** 3
        )

    for j in range(8):

        def panel(u, v):
            span = 1.015 - 0.23 * (1 - v) ** 1.5
            a = tau * (j + 0.5 + (u - 0.5) * span) / 8
            edge = hem(a)
            p, skin = cloth(a, edge + (0.999 - edge) * v)
            return p, (0.05 + 0.90 * u, 0.995 - 0.91 * v), skin

        patch(lining if j in (2, 6) else silk, 20, 36, panel)

        def trim(u, v):
            p, tex, skin = panel(0.022 * u, v)
            x, y, z = p
            return (x * 1.007, y, z * 1.008), tex, skin

        patch(brass if j % 2 == 0 else crimson, 2, 36, trim)

    # The paired pleated fields flank flat embroidered front and rear panels.
    # Their flared hem meets the leg weights of the existing split riding skirt.
    for side in (-1, 1):

        def pleats(u, v):
            a = side * (0.54 + 2.06 * u)
            edge = hem(a) + 0.012
            y = edge + (1.001 - edge) * v
            fold = (0.5 + 0.5 * cos(tau * 12 * u)) ** 2
            lift = 0.004 + (0.003 + 0.010 * (1 - v)) * fold
            (x, h, z), weights = cloth(a, y, lift)
            return (x, h, z), (u, 1 - v), weights

        patch(lining, 120, 24, pleats)
        for row, mat, width in ((0.025, crimson, 0.046), (0.080, brass, 0.007)):

            def border(u, v):
                (x, y, z), tex, weights = pleats(u, row + width * v)
                return (1.009 * x, y, 1.009 * z), tex, weights

            patch(mat, 120, 3, border)

    for side, suffix in [(-1, "r"), (1, "l")]:
        chain = [k + "_" + suffix for k in ("upperarm", "lowerarm", "hand")]

        def arm(u, v, ease=0):
            seg = min(1, int(2 * v))
            t = 2 * v - seg
            a, b = (rest[k] for k in chain[seg : seg + 2])
            axis = unit([j - i for i, j in zip(a, b)])
            n = unit(cross(axis, (0, 0, 1)))
            m = cross(axis, n)
            width = (
                (0.048 + 0.008 * smooth(v / 0.23)) * (1 - v)
                + 0.034 * v
                + 0.0025 * sin(10 * pi * v + 2 * cos(tau * u))
                + ease
            )
            p = tuple(
                a[k] * (1 - t)
                + b[k] * t
                + width * (n[k] * cos(tau * u) + m[k] * sin(tau * u))
                for k in range(3)
            )
            p = (p[0] - side * 0.014 * (1 - v) ** 1.3, p[1], p[2])
            return p, (u, 1 - v), [(chain[seg], 1 - t), (chain[seg + 1], t)]

        # Bare shoulder and upper arm between the two folds of the stole.
        def upper_skin(u, v):
            p, _, w = arm(u, 0.60 * v)
            return p, (0.64 + 0.016 * u, 0.64 + 0.016 * v), w

        patch(bare, 36, 24, upper_skin)
        patch(silk, 36, 20, lambda u, v: arm(u, 0.55 + 0.45 * v, 0.002))
        for i in range(6):
            patch(
                lining,
                40,
                4,
                lambda u, v: arm(
                    u, 0.55 + 0.065 * i + 0.041 * v + 0.017 * sin(tau * u), 0.0035
                ),
            )

        def sleeve_cap(u, v):
            ring, _, _ = arm(u, 0)
            joint = rest[chain[0]]
            centre = (joint[0] - side * 0.014, joint[1], joint[2])
            angle = v * pi / 2
            # The shoulder dome extends out of the sleeve opening along the
            # upper-arm axis, then joins the sloping bodice close to the neck.
            axis = unit([a - b for a, b in zip(centre, rest[chain[1]])])
            dome = 0.043 * sin(angle)
            p = tuple(
                centre[k] + (ring[k] - centre[k]) * cos(angle) + axis[k] * dome
                for k in range(3)
            )
            p = (p[0] - side * 0.010 * sin(angle), p[1] + 0.007 * sin(angle), p[2])
            blend = 0.60 * smooth(v)
            return (
                p,
                (u, 0.06 + 0.22 * v),
                [(chain[0], 1 - blend), ("clavicle_" + suffix, blend)],
            )

        def shoulder_skin(u, v):
            p, _, w = sleeve_cap(u, v)
            return p, (0.64 + 0.016 * u, 0.64 + 0.016 * v), w

        patch(bare, 36, 16, shoulder_skin)
        shoulder_silks(patch, arm, sleeve_cap, side, silk, lining, silver)

        # A dark, tapered bracer leaves the elbow free and tapers into the glove.
        patch(boots, 36, 22, lambda u, v: arm(u, 0.635 + 0.353 * v, ease=0.0022))
        for band, width, slot in (
            (0.635, 0.024, crimson),
            (0.665, 0.006, brass),
            (0.959, 0.018, crimson),
            (0.982, 0.005, brass),
        ):
            patch(slot, 36, 4, lambda u, v: arm(u, band + width * v, ease=0.0038))

    def belt(u, v, lift=0.006):
        a = tau * u
        y = 1.067 + 0.068 * v + 0.013 * sin(a - 0.55)
        p, skin = cloth(a, y, lift)
        return p, (u, v), skin

    patch(lining, 88, 10, belt)
    for band in (0.07, 0.87):
        patch(brass, 88, 3, lambda u, v: belt(u, band + 0.04 * v, 0.008))
    centre, _, buckle_skin = belt(0.034, 0.50, 0.009)
    globe(jade, centre, (0.021, 0.014, 0.008), buckle_skin)
    rear, _, rear_skin = belt(0.50, 0.48, 0.008)
    for side in (-1, 1):

        def loop(u, v):
            a = tau * v
            width = 0.018 * (2 * u - 1)
            return (
                (
                    side * (0.018 + 0.075 * (1 - cos(a)) / 2) + width * sin(a),
                    rear[1] + 0.018 * sin(a) + width * cos(a),
                    rear[2] - 0.018 * sin(pi * v) - 0.006 * cos(tau * u),
                ),
                (u, v),
                rear_skin,
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
            z = rear[2] - 0.008 - 0.135 * v + 0.012 * sin(5 * v) + crosswise * sin(roll)
            y = rear[1] - length * v + 0.022 * (1 - abs(2 * u - 1)) * v**12
            return (x, y, z), (u, v), rear_skin

        patch(river, 16, 48, streamer)
    globe(jade, rear, (0.018, 0.016, 0.010), rear_skin)
    riding_legs(patch, rest, trousers, boots, sole, lining, silver)
    regalia(patch, strand, globe, lapel_surface, silk, lining, silver, jade)
    finish({bare: skin_reflectance})
    finish_shapes()
