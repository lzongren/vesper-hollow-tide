"""Gold-wire ear pendants for the playable swordswoman."""

from math import cos, sin, tau


def pendants(strand, globe, jade, pearl, gold):
    for side in (-1, 1):
        pendant(strand, globe, jade, pearl, gold, side)


def pendant(strand, globe, jade, pearl, gold, side):
    head = [("head", 1)]
    x, y, z = side * 0.080, 1.629, 0.026
    globe(pearl, (x, y, z), (0.0031, 0.0034, 0.0031), head)

    # An open five-petal gold link lets the background show through.
    def link(t):
        a = tau * t
        radius = 0.0065 * (1 + 0.22 * cos(5 * a))
        return (
            x + side * 0.48 * radius * sin(a),
            y - 0.011 + radius * cos(a),
            z + 0.88 * radius * sin(a),
        )

    strand(gold, link, lambda t: 0.00065, head, 45)

    def chain(t):
        return (x + side * 0.0015 * t, y - 0.019 - 0.009 * t, z)

    strand(gold, chain, lambda t: 0.0006, head, 8)
    globe(jade, chain(1), (0.0029, 0.0056, 0.0031), head)
    globe(gold, (x + side * 0.0015, y - 0.034, z), (0.0012,) * 3, head)
