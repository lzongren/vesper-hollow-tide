"""Intersect horizontal head sections with radial lines to seat the hairline."""

from math import atan2, cos, exp, floor, sin, tau

from bind_pilgrim import cross, unit


def scalp_radius(vertices, faces):
    # A single forehead lookup serves both the hair cap and the temple strands.
    # Each row is sampled on the fitted head in the same units as its sculpt.
    low, step, columns = 6.48, 0.027, 112
    rows = []
    for j in range(74):
        y = low + j * step
        segments = []
        for f in faces:
            cut = []
            for k, index in enumerate(f):
                a, b = vertices[f[k - 1]], vertices[index]
                if (a[1] > y) == (b[1] > y):
                    continue
                t = (y - a[1]) / (b[1] - a[1])
                cut.append((a[0] + t * (b[0] - a[0]), a[2] + t * (b[2] - a[2]) - 0.56))
            if len(cut) == 2:
                segments.append(cut)
        row = []
        for i in range(columns):
            angle = i * tau / columns
            dx, dz = sin(angle), cos(angle)
            greatest = 0.0
            for (ax, az), (bx, bz) in segments:
                sx, sz = bx - ax, bz - az
                den = dx * sz - dz * sx
                if abs(den) < 1e-7:
                    continue
                t = (ax * dz - az * dx) / den
                if 0 <= t <= 1:
                    greatest = max(greatest, (ax * sz - az * sx) / den)
            row.append(greatest)
        rows.append(row)

    def radius(angle, y, default):
        col = (angle % tau) * columns / tau
        row = (y - low) / step
        j = floor(row)
        if not 0 <= j < len(rows) - 1:
            return default
        i = floor(col) % columns
        across, up = col - floor(col), row - j
        a, b = rows[j], rows[j + 1]
        right = (i + 1) % columns
        v = (1 - up) * (a[i] * (1 - across) + a[right] * across) + up * (
            b[i] * (1 - across) + b[right] * across
        )
        return v if v > 0 else default

    return radius


def fit_hair_margin(surface, edge_row):
    """Fit the ear-to-nape margin in rest metres and grow the root veil along it."""

    def smooth(t):
        t = min(1, max(0, t))
        return t * t * (3 - 2 * t)

    # Follow the opaque margin in the combed surface coordinates. At the
    # rear of the pinna the outermost scalp section changes from ear to
    # neck. Fit a continuous swept curve across that anatomical transition.
    samples = 192
    edge_points = []
    for i in range(samples):
        a = tau * i / samples
        row = edge_row(a)
        edge_points.append(surface(a, row))

    kernel = [exp(-0.5 * (k / 7.6) ** 2) for k in range(-20, 21)]
    total = sum(kernel)
    offsets = []
    for i, point in enumerate(edge_points):
        a = tau * i / samples
        azimuth = abs(atan2(sin(a), cos(a)))
        amount = smooth((azimuth - 1.38) / 0.27) * (1 - smooth((azimuth - 2.47) / 0.39))
        arc = [
            sum(
                w * edge_points[(i + k - 20) % samples][axis]
                for k, w in enumerate(kernel)
            )
            / total
            for axis in range(3)
        ]
        # Let the upper growth sweep a little towards the ear, then recede
        # toward the nape. Each side has a slightly different turn.
        side = 1 if sin(a) > 0 else -1
        arc[2] += 0.0044 * exp(-(((azimuth - 1.93 - 0.035 * side) / 0.26) ** 2))
        arc[2] -= 0.0030 * exp(-(((azimuth - 2.38) / 0.24) ** 2))
        offsets.append(tuple(amount * (new - old) for new, old in zip(arc, point)))

    # At the helix, lowering the sampled row can hit the ear itself. Grow
    # the outer fibers along the scalp tangent of the fitted margin. This
    # also keeps overlapping cards from folding back across one another.
    margin = [
        tuple(p + v for p, v in zip(point, shift))
        for point, shift in zip(edge_points, offsets)
    ]
    across = []
    for i, point in enumerate(margin):
        along = unit([j - k for j, k in zip(margin[(i + 1) % samples], margin[i - 1])])
        normal = unit((point[0], 0.25 * (point[1] - 1.66), point[2] - 0.025))
        down = unit(cross(normal, along))
        across.append(tuple(c * (1 if down[1] < 0 else -1) for c in down))

    def combed(a, row):
        p = surface(a, row)
        column = (a % tau) * samples / tau
        i = int(column)
        t = column - i
        edge = edge_row(a)
        keep = 1 - smooth((abs(row - edge) - 0.075) / 0.19)
        left, right = offsets[i % samples], offsets[(i + 1) % samples]
        shaped = tuple(
            p[j] + keep * ((1 - t) * left[j] + t * right[j]) for j in range(3)
        )
        azimuth = abs(atan2(sin(a), cos(a)))
        band = smooth((azimuth - 1.47) / 0.19) * (1 - smooth((azimuth - 2.34) / 0.30))
        depth = edge - row
        weight = band * smooth((depth + 0.026) / 0.026)
        if weight == 0:
            return shaped
        nxt = (i + 1) % samples
        reach = 0.153 * depth
        return tuple(
            shaped[j]
            + weight
            * (
                (1 - t) * (margin[i][j] + across[i][j] * reach)
                + t * (margin[nxt][j] + across[nxt][j] * reach)
                - shaped[j]
            )
            for j in range(3)
        )

    return combed
