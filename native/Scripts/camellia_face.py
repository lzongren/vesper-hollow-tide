"""Register the closed-lid complexion to the open eyes, nose and lips."""

from bisect import bisect_right
from math import exp, pi, sin

# Neutral head heights and image landmarks, measured independently.
FEATURES = (
    (5.8, 0.96),
    (6.18, 0.836),
    (6.46, 0.737),
    (6.604, 0.688),
    (6.79, 0.622),
    (6.92, 0.577),
    (7.11, 0.507),
    (7.284, 0.455),
    (7.51, 0.366),
    (7.75, 0.300),
    (8.11, 0.175),
    (8.58, 0.035),
)
HEIGHTS = tuple(height for height, _ in FEATURES)


def projection(x, y):
    k = min(len(FEATURES) - 2, max(0, bisect_right(HEIGHTS, y) - 1))
    a, b = FEATURES[k : k + 2]
    v = a[1] + (b[1] - a[1]) * (y - a[0]) / (b[0] - a[0])
    width = 0.391 - 0.034 * exp(-(((y - 6.65) / 0.29) ** 2))
    u = 0.504 + x * width
    # The portrait has closed eyes. Map its upper and lower skin onto the
    # corresponding lid, skipping the photographed lash fringe in between.
    t = min(1, max(0, (abs(x) - 0.158) / 0.308))
    span = sin(pi * t) ** 0.58
    axis = 7.268 + 0.021 * t
    if span and abs(y - axis) < 0.19:
        blend = max(0, 1 - (abs(y - axis) / 0.19) ** 2) ** 2 * span
        v += (-0.003 if y >= axis else 0.016) * blend
    return u, v
