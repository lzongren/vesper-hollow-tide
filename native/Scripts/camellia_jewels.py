"""Gold-wire ear pendants for the playable swordswoman."""

from math import cos, sin, tau


def pendants(strand, globe, jade, pearl, gold, scalp, faces):
    for side, anchor in zip((-1, 1), lobe_anchors(scalp, faces)):
        pendant(strand, globe, jade, pearl, gold, side, anchor)


def lobe_anchors(scalp, faces):
    """Raycast each stud against its own deformed lobe, in scalp coordinates."""
    # Piercing is approximately 8 mm above the free lobe edge. Coordinates
    # supplied by add_head use the same normalized frame as the hair fitter.
    y, z = 1.6075, 0.0160
    qy, qz = 7 + (y - 1.625) / 0.103, 0.32 + z / 0.104
    left, right = [], []
    for a, b, c in faces:
        pa, pb, pc = scalp[a], scalp[b], scalp[c]
        if not (
            min(pa[1], pb[1], pc[1]) <= qy <= max(pa[1], pb[1], pc[1])
            and min(pa[2], pb[2], pc[2]) <= qz <= max(pa[2], pb[2], pc[2])
        ):
            continue
        by, bz = pb[1] - pa[1], pb[2] - pa[2]
        cy, cz = pc[1] - pa[1], pc[2] - pa[2]
        det = by * cz - bz * cy
        if abs(det) < 1e-12:
            continue
        dy, dz = qy - pa[1], qz - pa[2]
        u, v = (dy * cz - dz * cy) / det, (by * dz - bz * dy) / det
        if min(u, v, 1 - u - v) >= -1e-7:
            x = 0.104 * (pa[0] + u * (pb[0] - pa[0]) + v * (pc[0] - pa[0]))
            (left if x < 0 else right).append(x)
    if not left or not right:
        raise ValueError("Ear studs missed the fitted earlobes")
    # A 3.1 mm pearl seats 1.0 mm into the skin on its medial face.
    return ((min(left) - 0.0021, y, z), (max(right) + 0.0021, y, z))


def pendant(strand, globe, jade, pearl, gold, side, anchor):
    head = [("head", 1)]
    x, y, z = anchor
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
