"""Sample the exact triangular valley floor in Unreal world centimetres."""

import math
import runpy


def sampler(project, valley):
    origin = valley.get_actor_location()
    read = runpy.run_path(str(project / "Scripts" / "bind_pilgrim.py"))["Glb"]
    terrain = read(project / "Art" / "MountainValley.glb")
    prim = terrain.doc["meshes"][0]["primitives"][0]
    verts = terrain.values(prim["attributes"]["POSITION"])
    side = math.isqrt(len(verts))
    step = verts[1][0] - verts[0][0]
    if side * side != len(verts) or step <= 0:
        raise RuntimeError("Unexpected valley grid")

    def ground(x, y):
        gx = ((x - origin.x) / 100 - verts[0][0]) / step
        gz = ((y - origin.y) / 100 - verts[0][2]) / step
        i, j = math.floor(gx), math.floor(gz)
        if not (0 <= i < side - 1 and 0 <= j < side - 1):
            raise RuntimeError("Tree outside the authored valley")
        u, v = gx - i, gz - j
        a = verts[j * side + i][1]
        b = verts[j * side + i + 1][1]
        c = verts[(j + 1) * side + i][1]
        d = verts[(j + 1) * side + i + 1][1]
        return origin.z + 100 * (
            a * (1 - max(u, v)) + b * max(0, u - v) + c * max(0, v - u) + d * min(u, v)
        )

    return ground
