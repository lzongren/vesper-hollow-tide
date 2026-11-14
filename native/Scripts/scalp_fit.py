"""Intersect horizontal head sections with radial lines to seat the hairline."""

from math import cos, floor, sin, tau


def scalp_radius(vertices, faces):
    # A single forehead lookup serves both the hair cap and the temple strands.
    # Each row is sampled on the fitted head in the same units as its sculpt.
    low, step, columns = 7.18, 0.027, 112
    rows = []
    for j in range(48):
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
