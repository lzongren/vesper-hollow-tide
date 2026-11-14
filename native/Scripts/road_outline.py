"""Compute exposed edges of the five road decks and three overlapping courts, in UE centimetres."""

import itertools
import math

POINTS = [(0, 0), (4200, 0), (7600, 1600), (11500, 1600), (14800, -800), (19400, -800)]


def rectangle(x, y, length, width, yaw=0):
    c, s = math.cos(yaw), math.sin(yaw)
    return [
        (
            x + i * length * c / 2 - j * width * s / 2,
            y + i * length * s / 2 + j * width * c / 2,
        )
        for i, j in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ]


def decks():
    result = []
    for a, b in itertools.pairwise(POINTS):
        dx, dy = b[0] - a[0], b[1] - a[1]
        result.append(
            rectangle(
                (a[0] + b[0]) / 2,
                (a[1] + b[1]) / 2,
                math.hypot(dx, dy) + 45,
                830,
                math.atan2(dy, dx),
            )
        )
    return result + [rectangle(x, y, 2920, 2800) for x, y in POINTS[1::2]]


def point(a, d, t):
    return a[0] + t * d[0], a[1] + t * d[1]


def boundary(polygons):
    def cross(a, b):
        return a[0] * b[1] - a[1] * b[0]

    def sub(a, b):
        return a[0] - b[0], a[1] - b[1]

    def edges(poly):
        return zip(poly, poly[1:] + poly[:1])

    def inside(p, poly):
        return all(cross(sub(b, a), sub(p, a)) >= -1e-6 for a, b in edges(poly))

    seen = set()
    for poly in polygons:
        for a, b in edges(poly):
            d = sub(b, a)
            length = math.hypot(*d)

            cuts = {0.0, 1.0}
            for other in polygons:
                if other is poly:
                    continue
                for c, e in edges(other):
                    v = sub(e, c)
                    den = cross(d, v)
                    if abs(den) < 1e-7:
                        if abs(cross(sub(c, a), d)) < 1e-6:
                            for vertex in (c, e):
                                t = (
                                    sum(i * j for i, j in zip(sub(vertex, a), d))
                                    / length**2
                                )
                                if 0 < t < 1:
                                    cuts.add(t)
                        continue
                    t = cross(sub(c, a), v) / den
                    u = cross(sub(c, a), d) / den
                    if 0 < t < 1 and -1e-8 <= u <= 1 + 1e-8:
                        cuts.add(t)
            cuts = sorted(cuts)
            for lo, hi in itertools.pairwise(cuts):
                if length * (hi - lo) < 0.05:
                    continue
                x, y = point(a, d, (lo + hi) / 2)
                outward = (x + d[1] / length * 0.02, y - d[0] / length * 0.02)
                if any(inside(outward, q) for q in polygons):
                    continue
                endpoints = point(a, d, lo), point(a, d, hi)
                key = tuple(sorted((round(x, 3), round(y, 3)) for x, y in endpoints))
                if key not in seen:
                    seen.add(key)
                    yield endpoints
