"""Open and dress the eyelids while keeping the lashes registered through a blink."""

from math import exp, pi, sin

from wayfarer_blink import lid_delta


def aperture(x, y, z):
    t = max(0, min(1, (abs(x) - 0.173) / 0.268))
    span = sin(pi * t) ** 0.66
    front = min(1, max(0, (z - 1.15) / 0.18))
    return 0.34 * span * front * exp(-(((y - 7.282) / 0.118) ** 2))


def blink_delta(x, y, z):
    dx, dy, dz = lid_delta(x, y, z)
    return dx, dy * (1 + aperture(x, y, z)), dz


def rim(t, ids, fitted, shifts):
    k = min(len(ids) - 2, int(t * (len(ids) - 1)))
    f = t * (len(ids) - 1) - k

    def lerp(a, b):
        return tuple((1 - f) * v + f * w for v, w in zip(a, b))

    return lerp(fitted[ids[k]], fitted[ids[k + 1]]), lerp(shifts[k], shifts[k + 1])


def eyelashes(out, slot, source, fitted, bone, displacements):
    # Follow the existing upper rim from the inner to the outer canthus.
    upper = (
        2287,
        2284,
        2281,
        2278,
        2275,
        2222,
        2221,
        2227,
        2230,
        2233,
        2236,
        2239,
        2242,
    )
    points, delta, indices = [], [], []
    for side in (-1, 1):
        ids = list(upper)
        if side < 0:
            ids = [
                min(
                    range(len(source)),
                    key=lambda j, i=i: (
                        (source[j][0] + source[i][0]) ** 2
                        + (source[j][1] - source[i][1]) ** 2
                        + (source[j][2] - source[i][2]) ** 2
                    ),
                )
                for i in upper
            ]
        shifts = [displacements[i] for i in ids]

        # The fine, dark strip also forms the lash roots at mid-distance.
        base = len(points)
        for j in range(41):
            t = j / 40
            (x, y, z), d = rim(t, ids, fitted, shifts)
            width = 0.00016 + 0.00067 * sin(pi * t) ** 0.65
            points.extend([(x, y - 0.00014, z + 0.00027), (x, y + width, z + 0.0005)])
            delta.extend([d, d])
            if j:
                k = base + 2 * j
                indices.extend([k - 2, k - 1, k + 1, k - 2, k + 1, k])
        for j in range(32):
            t = 0.045 + 0.88 * j / 31
            (x, y, z), d = rim(t, ids, fitted, shifts)
            length = (0.0012 + 0.0026 * sin(pi * t) ** 0.8) * (
                0.86 + 0.14 * sin(19 * j)
            )
            w = 0.00012 + 0.00009 * sin(pi * t)
            k = len(points)
            for row in range(4):
                v = row / 3
                shift = side * length * (0.22 + 0.64 * t) * v
                cy = y + length * v * (0.18 + 0.62 * v)
                cz = z + 0.00038 + length * (1.16 * v - 0.44 * v * v)
                points.extend(
                    [
                        (x + shift - w * (1 - v), cy, cz),
                        (x + shift + w * (1 - v), cy, cz),
                    ]
                )
                blink = (d[0], d[1] - length * 0.65 * v, d[2])
                delta.extend([blink, blink])
                if row:
                    a = k + 2 * row
                    indices.extend([a - 2, a - 1, a + 1, a - 2, a + 1, a])
    n = len(points)
    out.doc["meshes"][0]["primitives"].append(
        {
            "attributes": {
                "POSITION": out.data(points, "VEC3", bounds=True),
                "NORMAL": out.data([(0, 0.2, 0.9798)] * n, "VEC3"),
                "JOINTS_0": out.data([(bone, 0, 0, 0)] * n, "VEC4", 5123),
                "WEIGHTS_0": out.data([(1, 0, 0, 0)] * n, "VEC4"),
            },
            "material": slot,
            "indices": out.data([(i,) for i in indices], "SCALAR", 5125),
        }
    )
    return out.data(delta, "VEC3", bounds=True)
