"""A pierced gilt swallow hairpin with layered enamel flight feathers.

The ornament follows the curvature of the chignon. Its outer wing breaks the
silhouette in the portrait, while the second wing reads from the player's camera.
"""

from math import pi, sin


def swallow(patch, strand, globe, gold, jade, enamel, pearl):
    head = [("head", 1)]

    # Millimetres in the jeweller's drawing. The face of the pin wraps around
    # the left ear, with raised wire and the setting in front of the enamel.
    def mount(x, y, depth=0):
        return (
            -0.090 - x * 0.00076 - depth * 0.00064,
            1.717 + y * 0.001,
            -0.065 - x * 0.00064 + depth * 0.00076,
        )

    def wire(path, gauge, steps=28):
        strand(gold, lambda t: mount(*path(t)), lambda t: gauge * 0.001, head, steps)

    def feather(root, tip, width, bend, slot):
        dx, dy = tip[0] - root[0], tip[1] - root[1]
        length = (dx * dx + dy * dy) ** 0.5
        nx, ny = -dy / length, dx / length

        def blade(u, v):
            curve = sin(pi * v)
            breadth = width * curve**0.84
            lateral = bend * curve + (u * 2 - 1) * breadth
            return (
                root[0] + dx * v + nx * lateral,
                root[1] + dy * v + ny * lateral,
                1.2 + 2.4 * curve * (1 - (2 * u - 1) ** 2),
            )

        patch(slot, 8, 24, lambda u, v: (mount(*blade(u, v)), (u, v), head))
        for edge in (0, 1):
            wire(lambda t, edge=edge: blade(edge, t), 0.70)
        wire(lambda t: blade(0.50, t), 0.45)

    # A back pin disappears into the coil. Two tail streamers fork away from
    # the body; the primary feathers fan outward in a single swept wing.
    wire(lambda t: (-44 + 67 * t, -9 + 12 * t, 0), 1.35)
    for idx, tip in enumerate(((5, 45), (20, 53), (35, 51), (49, 43), (55, 33))):
        feather((0, 1 + idx * 0.9), tip, 4.0, 3.2, jade if idx % 3 == 0 else enamel)
    for x, y in ((-32, 26), (-37, 17), (-40, 7)):
        feather((-2, 0), (x, y), 3.6, -2.8, enamel)
    for tip in ((4, -28), (22, -22)):
        feather((-3, 0), tip, 2.8, 1.7, jade)
    feather((-4, -9), (0, 17), 5.2, -1.6, enamel)
    globe(gold, mount(-1, 16, 3), (0.0048, 0.0051, 0.0046), head)
    globe(pearl, mount(-2, 17, 7), (0.0016,) * 3, head)
    wire(lambda t: (-4 - 8 * t, 16 + 1.8 * t, 4), 0.82)
    # Graduated pearl drops stay close to the ear, clear of the collar.
    for x, y, length in ((5, -25, 21), (20, -20, 34)):
        wire(
            lambda t, x=x, y=y, length=length: (
                x + 1.2 * sin(pi * t),
                y - length * t,
                1,
            ),
            0.55,
        )
        for t in (0.42, 0.72, 1):
            globe(
                pearl,
                mount(x + 1.2 * sin(pi * t), y - length * t, 1),
                (0.0021, 0.0030, 0.0021),
                head,
            )
