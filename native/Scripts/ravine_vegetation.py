"""Plant the path verge in patches and drive gentle wind through the stem tips."""

from math import cos, sin, tau
from random import Random


def plant(groups, surface, clearance, marker):
    rng = Random(51579)
    mx, my = marker
    # Nest the vertical face in an irregular collar of fallen stone.
    for j in range(30):
        # A broken ledge sheds material into two pockets. Small fragments
        # trail away from the nearer pocket without enclosing the visitor.
        left = j < 19
        centre_x, centre_y = (-2.02, 0.51) if left else (2.13, -0.42)
        size = rng.uniform(0.16, 0.49) if left else rng.uniform(0.26, 0.64)
        if j % 5 == 0:
            size *= 0.50
            centre_y += 0.86
        x = mx + centre_x + rng.uniform(-0.76, 0.68)
        y = my + centre_y + rng.uniform(-0.68, 0.83)
        if clearance(x, y) < 1.3:
            continue
        z, _ = surface(x, y)
        scale = size
        groups[rng.randrange(6)].append(
            (
                x,
                y,
                z - 0.17 * scale,
                rng.uniform(-16, 16),
                rng.uniform(-13, 13),
                rng.uniform(-180, 180),
                scale,
            )
        )
    # Colonies collect along the stair landing and at the bases of the fans.
    # A second, finer scale crowds plants around each colony's centre.
    for _ in range(530):
        x = rng.uniform(177, 220)
        y = rng.uniform(-76, -29)
        if clearance(x, y) < 0.35:
            continue
        _, depth = surface(x, y)
        island = 0.5 + 0.5 * sin(0.54 * x + 0.22 * y + 1.4 * sin(y * 0.31)) * cos(
            x * 0.19 - y * 0.42
        )
        if rng.random() > 0.20 + 0.64 * island or depth > 1.0:
            continue
        extent = rng.uniform(0.42, 2.15)
        for _ in range(rng.randint(8, 28)):
            a = rng.uniform(0, tau)
            r = extent * rng.random() ** 0.59
            px, py = x + r * cos(a), y + 0.70 * r * sin(a)
            if clearance(px, py) < 0.32:
                continue
            z, h = surface(px, py)
            if h > 1.05:
                continue
            floral = rng.random() < 0.11
            variant = rng.randrange(5)
            idx = (12 if floral else 7) + variant
            scale = rng.uniform(1.0, 1.85) if floral else rng.uniform(0.84, 1.58)
            groups[idx].append(
                (
                    px,
                    py,
                    z - 0.012,
                    0,
                    rng.uniform(-5, 5),
                    rng.uniform(-180, 180),
                    scale,
                )
            )
