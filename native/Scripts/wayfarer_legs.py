"""Fit the trousers and shaped riding boots around the player's leg and foot joints."""

from math import cos, pi, sin, tau
from bisect import bisect_right


def riding_legs(patch, rest, trouser, leather, sole, red, gold):
    # Height, lateral radius and depth measured in metres on one leg.
    sections = (
        (0.080, 0.033, 0.039),
        (0.13, 0.034, 0.043),
        (0.22, 0.036, 0.043),
        (0.31, 0.051, 0.058),
        (0.37, 0.055, 0.064),
        (0.445, 0.049, 0.052),
        (0.50, 0.052, 0.056),
        (0.565, 0.054, 0.058),
        (0.66, 0.063, 0.069),
        (0.77, 0.081, 0.085),
        (0.88, 0.089, 0.101),
        (0.96, 0.090, 0.106),
        (0.99, 0.085, 0.101),
    )
    heights = tuple(row[0] for row in sections)

    def ease(t):
        t = min(1, max(0, t))
        return t * t * (3 - 2 * t)

    for side, suffix in ((1, "l"), (-1, "r")):
        thigh, calf, foot, ball = (
            key + "_" + suffix for key in ("thigh", "calf", "foot", "ball")
        )
        hip, knee, ankle, toe = (rest[k] for k in (thigh, calf, foot, ball))

        def leg(u, y, lift=0):
            lo = min(len(sections) - 2, max(0, bisect_right(heights, y) - 1))
            p, q = sections[lo : lo + 2]
            f = (y - p[0]) / (q[0] - p[0])
            rx = p[1] + (q[1] - p[1]) * f + lift
            rz = p[2] + (q[2] - p[2]) * f + lift
            a, b = (ankle, knee) if y < knee[1] else (knee, hip)
            t = (y - a[1]) / (b[1] - a[1])
            cx = a[0] + (b[0] - a[0]) * t
            cz = a[2] + (b[2] - a[2]) * t
            # Tuck the upper thigh inside the joined trouser yoke.
            tucked = ease((y - 0.71) / 0.175)
            cx *= 1 - 0.17 * tucked
            rx *= 1 - 0.25 * tucked
            rz *= 1 - 0.27 * tucked
            # The upper calf swells behind the tibia, the knee faces forward.
            cz -= 0.013 * max(0, 1 - abs(y - 0.365) / 0.10)
            cz += 0.011 * max(0, 1 - abs(y - 0.51) / 0.065)
            ang = tau * u
            pos = (cx + rx * sin(ang), y, cz + rz * cos(ang))
            top = 0.30 * ease((y - 0.865) / 0.125)
            shank = 1 - ease((y - 0.45) / 0.12)
            boot = 0.38 * (1 - ease((y - 0.080) / 0.06))
            return (
                pos,
                (u, (y - 0.08) / 0.91),
                [
                    (thigh, 1 - top - shank),
                    (calf, shank - boot),
                    (foot, boot),
                    ("pelvis", top),
                ],
            )

        patch(trouser, 40, 36, lambda u, v: leg(u, 0.080 + 0.834 * v))

        # A curved opening rises towards the outside of each shin.
        def cuff_height(u):
            return 0.421 + 0.029 * side * sin(tau * u) + 0.012 * cos(tau * u)

        def shaft(u, v):
            return leg(u, 0.081 + (cuff_height(u) - 0.081) * v, 0.0045)

        patch(leather, 40, 28, shaft)
        for slot, drop, width in ((red, 0, 0.012), (gold, 0.015, 0.0025)):
            patch(
                slot,
                40,
                3,
                lambda u, v: leg(u, cuff_height(u) - drop - width * v, 0.0068),
            )
        for turn in (0, 0.5):

            def spiral(u, v):
                a = (turn + 0.86 * v + 0.013 * u) % 1
                return leg(a, 0.151 + 0.21 * v, 0.0066)

            patch(red, 3, 36, spiral)
        # Closed shoe sections follow the ankle-to-ball axis instead of an open tube.
        foot_len = 0.265

        def shoe(u, v, layer):
            angle = tau * u
            width = (0.029 + 0.020 * sin(pi * v) ** 0.75) * (
                0.34 + 0.66 * sin(pi * v) ** 0.28
            )
            z = ankle[2] - 0.066 + foot_len * v
            cx = ankle[0] + (toe[0] - ankle[0]) * v
            base = 0.008 + 0.013 * ease((v - 0.74) / 0.26)
            high = 0.052 + 0.077 * max(0, 1 - abs(v - 0.37) / 0.57) ** 1.55
            if layer:
                width += 0.002
                h = 0.012
            else:
                h = high
            y = base + h * (0.5 + 0.5 * sin(angle))
            along = ease((v - 0.56) / 0.34)
            return (
                (cx + width * cos(angle), y, z),
                (u, v),
                [(foot, 1 - along), (ball, along)],
            )

        patch(leather, 30, 30, lambda u, v: shoe(u, v, False))
        patch(sole, 30, 30, lambda u, v: shoe(u, v, True))
        for end in (0, 1):

            def cap(u, v):
                p, uv, w = shoe(u, end, False)
                mid = shoe(0.75, end, False)[0]
                return (
                    (mid[0] + (p[0] - mid[0]) * v, mid[1] + (p[1] - mid[1]) * v, p[2]),
                    uv,
                    w,
                )

            patch(leather, 30, 4, cap)
