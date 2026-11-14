"""Openwork butterfly pin, with celadon enamel cells framed by gilt wire."""

from math import cos, pi, sin


def butterfly(patch, strand, globe, brass, enamel, pearl, head):
    # Project the pin across the three-quarter silhouette. Its back sits
    # inside the coil, and the two open wings curve around the temple.
    def place(x, y, lift=0):
        return (
            0.084 + 0.84 * x + 0.53 * lift,
            1.772 + y + 0.12 * x,
            -0.046 - 0.53 * x + 0.84 * lift,
        )

    def curve(points, t):
        s = 1 - t
        return tuple(
            s**3 * a + 3 * s * s * t * b + 3 * s * t * t * c + t**3 * d
            for a, b, c, d in zip(*points)
        )

    def wire(path, radius, steps=18):
        strand(brass, path, lambda t: radius, head, steps)

    for sign in (-1, 1):
        for upper in (True, False):
            rim = (
                ((0.002, 0.001), (0.009, 0.023), (0.031, 0.046), (0.043, 0.040))
                if upper
                else (
                    (0.003, -0.004),
                    (0.026, -0.008),
                    (0.037, -0.020),
                    (0.025, -0.029),
                )
            )
            back = (
                ((0.043, 0.040), (0.051, 0.017), (0.025, 0.006), (0.002, 0.001))
                if upper
                else (
                    (0.025, -0.029),
                    (0.009, -0.032),
                    (0.005, -0.016),
                    (0.003, -0.004),
                )
            )

            def wing(s, t):
                a, b = curve(rim, t), curve(back, 1 - t)
                x, y = (a[0] * (1 - s) + b[0] * s, a[1] * (1 - s) + b[1] * s)
                lift = 0.21 * x + 0.0036 * sin(pi * t) * sin(pi * s)
                return place(sign * x, y, lift)

            def cell(u, v):
                return wing(0.10 + 0.80 * u, 0.11 + 0.77 * v), (u, v), head

            patch(enamel, 8, 18, cell)
            for u in (0, 1):
                wire(lambda t, u=u: wing(u, t), 0.00093)
            wire(lambda t: wing(0.47, t), 0.00060)
            for v in (0.35, 0.65):
                wire(lambda t, v=v: wing(t, v + 0.09 * sin(pi * t)), 0.00050)
        wire(
            lambda t: place(
                sign * (0.001 + 0.010 * t * t), 0.013 + 0.018 * t, 0.002 + 0.004 * t
            ),
            0.00075,
        )
        globe(pearl, place(sign * 0.011, 0.031, 0.006), (0.0018,) * 3, head)
    strand(
        brass,
        lambda t: place(0, -0.011 + 0.028 * t, 0.005),
        lambda t: 0.0018 + 0.0013 * sin(pi * t),
        head,
    )
    globe(pearl, place(0, 0.016, 0.005), (0.0034,) * 3, head)
