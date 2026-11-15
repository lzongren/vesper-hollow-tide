"""Half-up willow locks and an ivory magnolia comb on the combat skeleton."""

from math import cos, pi, sin, tau


def coiffure(patch, strand, globe, shell, hair, temple_hair, jade, pearl, brass):
    head = [("head", 1)]

    def card(u, v, index):
        return ((index % 4 + 0.001 + 0.998 * u) / 4, v)

    # Overlapping locks follow the shoulder blades as the head turns. The
    # outer layers fall to different lengths to preserve separate silhouettes.
    for k in range(17):
        layer = k // 9
        a = (k % 9) / (8 if layer == 0 else 7) * 2 - 1
        length = 0.37 + 0.15 * (1 - abs(a)) + 0.045 * sin(5.3 * k)
        width = 0.018 + 0.006 * (1 - abs(a))

        def back(u, v):
            s = v * v * (3 - 2 * v)
            x = a * (0.048 + 0.058 * sin(0.85 * pi * v)) + 0.021 * v * sin(
                7 * v + 2 * a
            )
            y = 1.715 - length * v
            z = -0.095 - 0.100 * sin(0.62 * pi * v) - 0.007 * layer
            z += 0.022 * abs(a) ** 2 - 0.008 * sin(6 * v + k)
            across = (2 * u - 1) * width
            curl = 0.45 * a + 0.42 * sin(5 * v + k)
            p = (
                x + across * cos(curl),
                y,
                z + across * sin(curl) - 0.005 * sin(pi * u),
            )
            neck = 0.42 * sin(pi * v) ** 2
            return (
                p,
                card(u, v, k),
                [
                    ("head", (1 - s) * (1 - neck)),
                    ("neck_01", neck),
                    ("spine_05", s * (1 - neck)),
                ],
            )

        patch(hair, 6, 28, back)

    # Side pieces frame the cheeks, pass in front of the ears and taper at the collar.
    for side in (-1, 1):
        for k in range(7):
            root = shell(side * (1.05 + k * 0.047), 0.14)

            def cheek(u, v):
                # Bury the cut root and ease the width out through the combed shell.
                emerge = min(1.0, v / 0.28)
                emerge = emerge * emerge * (3 - 2 * emerge)
                w = (
                    (2 * u - 1)
                    * (0.0023 + 0.0004 * sin(k * 3))
                    * (0.32 + 0.68 * emerge)
                    * (1 - 0.84 * v**2)
                )
                x = root[0] + side * (
                    0.015 * sin(pi * v) + 0.010 * v + w - 0.008 * (1 - emerge)
                )
                y = root[1] - (0.045 + 0.017 * ((k * 3) % 5)) * v
                z = (
                    root[2]
                    - (0.018 + 0.002 * k) * v
                    + 0.010 * sin(v * tau)
                    - 0.55 * w
                    - 0.006 * (1 - emerge)
                )
                return (x, y, z), card(u, v, k), head

            patch(temple_hair, 6, 26, cheek)

    # A curved gilt twig has three differently opened magnolias. Petals are
    # shallow shells with rolled rims and upward-curled tips.
    def twig(t):
        return (
            0.024 + 0.076 * t,
            1.695 + 0.053 * t - 0.014 * t * t,
            -0.114 + 0.061 * t,
        )

    strand(brass, twig, lambda t: 0.0025 - 0.0016 * t, head, 32)
    for j, (t, size) in enumerate(((0.44, 0.013), (0.80, 0.020), (0.99, 0.010))):
        x, y, z = twig(t)
        for ring, count in ((0, 5), (1, 4)):
            for k in range(count):
                a = tau * k / count + 0.65 * ring + 0.35 * j

                def petal(u, v):
                    span = (2 * u - 1) * size * 0.35 * sin(pi * v) ** 0.78
                    d = size * (1 - 0.34 * ring) * (0.06 + 0.94 * v)
                    across = d * cos(a) - span * sin(a)
                    rise = d * sin(a) + span * cos(a)
                    cup = size * (
                        0.13 + 0.14 * ring + 0.38 * v**2 + 0.12 * (2 * u - 1) ** 2
                    )
                    return (
                        (
                            x + 0.87 * across + 0.49 * cup,
                            y + rise,
                            z - 0.49 * across + 0.87 * cup,
                        ),
                        (u, v),
                        head,
                    )

                patch(jade, 8, 12, petal)
        globe(pearl, (x + 0.0015, y, z + 0.004), (0.0034,) * 3, head)
    for j, t in enumerate((0.67, 0.82)):
        x, y, z = twig(t)
        length = 0.047 + 0.025 * j

        def drop(v):
            return (x + 0.002 * sin(pi * v), y - length * v, z + 0.004 * v)

        strand(brass, drop, lambda v: 0.0007, head)
        for v in (0.42, 0.74, 1):
            globe(pearl, drop(v), (0.0022, 0.0036, 0.0022), head)
