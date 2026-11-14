"""Build skinned cloth panels and curved fittings from their rest-pose surfaces."""

from bind_pilgrim import cross, unit


def garment_surfaces(out, bones):
    batches = {}

    def patch(slot, cols, rows, fn):
        p, n, uv, j, w, idx = batches.setdefault(slot, ([], [], [], [], [], []))
        first = len(p)
        for r in range(rows + 1):
            v = r / rows
            for c in range(cols + 1):
                u = c / cols
                pos, tex, skin = fn(u, v)
                p.append(pos)
                uv.append(tex)
                j.append(tuple(([bones[b] for b, _ in skin] + [0] * 4)[:4]))
                w.append(tuple(([weight for _, weight in skin] + [0.0] * 4)[:4]))
                a = fn(min(1, u + 0.001), v)[0]
                b = fn(max(0, u - 0.001), v)[0]
                d = fn(u, min(1, v + 0.001))[0]
                e = fn(u, max(0, v - 0.001))[0]
                n.append(
                    unit(
                        cross(
                            tuple(x - y for x, y in zip(a, b)),
                            tuple(x - y for x, y in zip(d, e)),
                        )
                    )
                )
                if c and r:
                    k = first + r * (cols + 1) + c
                    idx.extend([k - cols - 2, k - cols - 1, k, k - cols - 2, k, k - 1])

    def finish():
        for slot, (p, n, uv, j, w, idx) in batches.items():
            attrs = dict(
                POSITION=out.data(p, "VEC3", bounds=True),
                NORMAL=out.data(n, "VEC3"),
                TEXCOORD_0=out.data(uv, "VEC2"),
                JOINTS_0=out.data(j, "VEC4", 5123),
                WEIGHTS_0=out.data(w, "VEC4"),
            )
            out.doc["meshes"][0]["primitives"].append(
                dict(
                    attributes=attrs,
                    indices=out.data([(i,) for i in idx], "SCALAR", 5125),
                    material=slot,
                )
            )

    return patch, finish
