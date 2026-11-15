"""Four embroidered ruyi lobes fitted over the collarbones and upper arms."""

from math import cos, pi, sin


def cloud_collar(patch, brocade, piping, binding):
    # Cross sections follow the shoulder crest before falling over the sleeves.
    # Each section is (side radius, front depth, side height, front height).
    rings = (
        (0.061, 0.069, 1.519, 1.495),
        (0.103, 0.101, 1.512, 1.467),
        (0.154, 0.127, 1.518, 1.434),
        (0.201, 0.145, 1.503, 1.403),
        (0.233, 0.157, 1.451, 1.371),
        (0.260, 0.165, 1.411, 1.339),
        (0.282, 0.163, 1.376, 1.306),
        (0.310, 0.157, 1.340, 1.274),
    )

    def drape(angle, v, lift):
        side = sin(angle)
        # Scallop the lower edge but keep the throat and shoulder crest continuous.
        lobe = 0.5 + 0.5 * cos(4 * angle)
        reach = v * (0.77 - (1 - lobe) * 0.37 * v)
        reach *= 1 - 0.49 * abs(side) ** 2
        t = min(len(rings) - 1, reach * (len(rings) - 1))
        k = min(int(t), len(rings) - 2)
        fraction = t - k
        width, depth, shoulder, chest = (
            a + (b - a) * fraction for a, b in zip(rings[k], rings[k + 1])
        )
        side_amount = abs(side) ** 2.8
        x = (width + lift) * side
        y = chest + (shoulder - chest) * side_amount + lift
        z = (depth + lift) * cos(angle) + 0.010 - 0.032 * side_amount * v
        y -= 0.033 * side_amount * min(1.0, v / 0.65)
        arm = min(0.96, max(0, (abs(x) - 0.082) / 0.096)) * side_amount
        weights = [
            ("spine_05", 1 - arm),
            ("upperarm_l" if side > 0 else "upperarm_r", arm),
        ]
        return (x, y, z), weights

    for quarter in range(4):

        def section(u, v, lift=0, quarter=quarter):
            # Four separate silk leaves share a circular neckband. The
            # narrow tips expose the ivory coat between the shoulder and bib.
            split = max(0.0, (v - 0.20) / 0.80)
            span = 1 - 0.77 * split**1.16
            angle = (quarter + (u - 0.5) * span) * pi / 2
            p, weights = drape(angle, v, lift)
            return p, (u, v), weights

        patch(brocade, 48, 35, section)

        for side in (0, 1):

            def selvedge(u, v, side=side, section=section):
                t = 0.30 + 0.70 * v
                p, _, w = section(0.010 * u if side == 0 else 1 - 0.010 * u, t, 0.0015)
                return p, (u, v), w

            patch(piping, 2, 30, selvedge)

        for slot, lo, hi in (
            (binding, 0.910, 1.000),
            (piping, 0.913, 0.926),
            (piping, 0.971, 0.989),
            (piping, 0.014, 0.029),
        ):

            def braid(u, v, section=section, lo=lo, hi=hi, slot=slot):
                t = lo + (hi - lo) * v
                p, _, weights = section(u, t, 0.0012 if slot == binding else 0.0025)
                return p, (u * 2, v), weights

            patch(slot, 48, 3, braid)
