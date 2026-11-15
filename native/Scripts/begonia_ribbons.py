"""Fold silk around the chignon and skin the two loose ends to the upper back."""

from math import cos, pi, sin, tau


def knot(patch, globe, strand, silk, brass, pearl):
    head = [("head", 1)]
    # A wide, folded knot hugs the far surface of the coiled black hair.
    for side in (-1, 1):

        def loop(u, v):
            a = v * tau
            spread = sin(0.5 * a)
            bend = 0.5 - 0.5 * cos(a)
            cross = (u - 0.5) * 0.020 * (0.5 + 0.5 * spread)
            return (
                (
                    -0.018 + side * (0.008 + 0.049 * bend),
                    1.705 + 0.013 * sin(a) + cross,
                    -0.150 - 0.019 * spread + 0.012 * bend + 0.52 * cross,
                ),
                (u, v),
                head,
            )

        patch(silk, 10, 36, loop)

        def fall(u, v):
            ease = v * v * (3 - 2 * v)
            twist = side * (0.35 + 0.65 * sin(1.7 * pi * v + 0.3))
            width = (u - 0.5) * (0.019 + 0.014 * sin(pi * v * 0.86))
            # Tips are cut on a shallow bias, like a hand-finished silk tape.
            length = 0.292 if side < 0 else 0.225
            y = 1.699 - length * v + 0.010 * (u - 0.5) * v**6
            x = (
                -0.018
                + side * (0.015 + 0.078 * sin(v * pi * 0.68))
                + 0.015 * sin(5 * v)
                + width * cos(twist)
            )
            z = (
                -0.152
                - 0.052 * sin(0.64 * pi * v)
                + width * sin(twist)
                - 0.003 * sin(u * pi)
            )
            neck = 0.34 * sin(pi * v) ** 2
            return (
                (x, y, z),
                (u, v),
                [
                    ("head", (1 - ease) * (1 - neck)),
                    ("neck_01", neck),
                    ("spine_05", ease * (1 - neck)),
                ],
            )

        patch(silk, 12, 40, fall)
    # Tiny gold petals frame a seed-pearl clasp at the knot.
    for i in range(5):
        a = i * tau / 5

        def petal(t):
            b = t * tau
            d = 0.0048 * (1 - cos(b))
            w = 0.0032 * sin(b)
            return (
                -0.018 + d * cos(a) - w * sin(a),
                1.705 + d * sin(a) + w * cos(a),
                -0.155 - 0.002 * sin(pi * t),
            )

        strand(brass, petal, lambda t: 0.00085, head, 20)
    globe(pearl, (-0.018, 1.705, -0.160), (0.0033,) * 3, head)
