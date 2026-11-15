"""Porcelain ritual crown, crossed stole and pleated shoulder streamers."""

from math import cos, pi, sin, tau


def regalia(patch, strand, globe, cloth, silk, sage, silver, jade):
    head = [("head", 1)]

    def crown(a, t, lift=0):
        # A flattened, slightly backswept crown, seated around the chignon.
        w = 0.088 * (1 - 0.51 * t) + 0.007 * sin(pi * t)
        d = 0.077 * (1 - 0.43 * t)
        return (
            (w + lift) * sin(a),
            1.746 + 0.224 * t + 0.014 * cos(2 * a) * t,
            -0.016 - 0.035 * t + (d + lift) * cos(a),
        )

    for j in range(10):

        def leaf(u, v):
            # A small cutout between the porcelain facets shows the inner lining.
            a = tau * (j + (u - 0.5) * (0.83 - 0.12 * sin(pi * v))) / 10
            return crown(a, v), (u, v), head

        patch(silk, 12, 32, leaf)
        for side in (-1, 1):
            strand(
                silver,
                lambda t: crown(tau * (j + side * 0.43) / 10, t, 0.0015),
                lambda t: 0.0015,
                head,
                32,
            )
        # Opposing wires make an open lozenge above the brow.
        for k in range(3):
            for side in (-1, 1):
                strand(
                    sage,
                    lambda t: crown(
                        tau * (j + side * (t - 0.5) * 0.83) / 10, (k + t) / 3, 0.0028
                    ),
                    lambda t: 0.00095,
                    head,
                    24,
                )
    for t in (0.019, 0.055, 0.972):
        strand(silver, lambda u: crown(tau * u, t, 0.003), lambda u: 0.0022, head, 64)
    globe(jade, crown(0, 0.44, 0.006), (0.006, 0.012, 0.004), head)

    # The pierced front tablet carries a series of overlapping silver petals.
    for row in range(5):
        for side in (-1, 1):

            def petal(u, v):
                t = 0.11 + 0.14 * row + 0.16 * v
                a = side * (
                    0.19 * sin(pi * v) + 0.06 * v + (u - 0.5) * 0.18 * sin(pi * v)
                )
                return crown(a, t, 0.0054 + 0.002 * sin(pi * v)), (u, v), head

            patch(silver, 8, 16, petal)

    for side in (-1, 1):

        def stole(u, v, raise_by=0):
            # Cross over the ribs and broaden at the collarbones.
            # Turn both long strips behind the nape and meet at the back.
            turn = max(0, (v - 0.78) / 0.22)
            turn = turn * turn * (3 - 2 * turn)
            y = 1.023 + 0.47 * min(v / 0.88, 1) - 0.014 * turn
            middle = side * (-0.24 + 1.12 * v**1.22 + (pi - 0.88) * turn)
            width = 0.36 + 0.25 * sin(pi * v * 0.84)
            a = middle + (u - 0.5) * width
            pleat = 0.004 * (0.5 + 0.5 * cos(u * tau * 3 + 0.7 * v)) ** 2
            pos, w = cloth(
                a, y, 0.0032 + pleat * 0.6 + raise_by + (0.002 if side > 0 else 0)
            )
            return pos, (u, 0.05 + 0.90 * v), w

        patch(silk, 34, 56, stole)
        for edge in (0.016, 0.961):
            patch(silver, 3, 48, lambda u, v: stole(edge + 0.018 * u, v, 0.002))


def shoulder_silks(patch, arm, cap, side, ivory, sage, silver):
    outer = 0.5 if side > 0 else 0

    def mantle(u, v, lift=0.002):
        a = outer + (u - 0.5) * 0.46 + 0.075
        # Wrap continuously across the sleeve-cap seam, following exactly
        # the cap's skin weights and then the animated sleeve's weights.
        reach = v * (0.90 + 0.10 * cos(tau * 3 * u))
        if reach < 0.42:
            p, _, w = cap(a, 0.82 * (1 - reach / 0.42))
        else:
            p, _, w = arm(a, 0.195 * (reach - 0.42) / 0.58)
        ridge = lift + 0.0017 * sin(pi * v) * cos(tau * 5 * u)
        return (
            (
                p[0] + side * ridge * cos(tau * (a - outer)),
                p[1] + ridge * 0.7,
                p[2] - ridge * sin(tau * a),
            ),
            (u, v),
            w,
        )

    # Slender overlapping leaves reveal the shoulder between the folds.
    for layer in range(3):

        def leaf(u, v):
            local = (layer + 0.5 + (u - 0.5) * (0.97 - 0.49 * v * v)) / 3
            return mantle(local, v)

        patch(ivory if layer != 1 else sage, 18, 30, leaf)
    for row in (0.85, 0.95):
        patch(silver, 48, 3, lambda u, v: mantle(u, row + 0.018 * v, 0.0036))
    # Each overlapping tail follows the outside of the upper arm, with
    # staggered length and increasing clearance as it falls behind the elbow.
    for j in range(8):
        across = 0.13 + 0.091 * j
        length = 0.25 + 0.49 * j / 7

        def strip(u, v):
            spread = (u - 0.5) * 0.16 * (1 - v**3)
            a = outer + (across - 0.48) * 0.64 + spread
            p, _, w = arm(a, 0.17 + length * v, 0.006 + 0.003 * sin(pi * v))
            away = 0.006 + 0.033 * v + 0.018 * sin(pi * v) * sin(j)
            return (
                (
                    p[0] + side * away,
                    p[1] - 0.046 * v * v,
                    p[2] - (0.030 + 0.079 * j / 7) * v * v,
                ),
                (u, v),
                w,
            )

        patch(sage if j % 3 == 1 else ivory, 10, 30, strip)

        def edge(u, v):
            p, uv, w = strip(0.10 + 0.055 * u, v)
            return (p[0] + side * 0.001, p[1], p[2]), uv, w

        patch(silver, 2, 30, edge)
