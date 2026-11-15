"""Extract the registered adult head displacement from the CC0 MakeHuman target.

Pass the upstream base.obj and asian-female-young.target, in that order.
The neutral head in the game is an exact vertex subset of that base.
"""

import json
import sys
from pathlib import Path

directory = Path(__file__).resolve().parents[1] / "native/Art/Wayfarer"
source = json.loads((directory / "head.json").read_text())["vertices"]
obj, target = map(Path, sys.argv[1:])
base = [
    tuple(map(float, line.split()[1:4]))
    for line in obj.read_text().splitlines()
    if line.startswith("v ")
]
index = {point: i for i, point in enumerate(base)}
offset = {
    int(parts[0]): tuple(map(float, parts[1:4]))
    for row in target.read_text().splitlines()
    if (parts := row.split()) and parts[0].isdigit()
}
# The full-body target changes stature. Register both eye sockets back to the
# rig and taper into the original neck so the head still fits the collar.
eye = [
    index[tuple(p)]
    for p in source
    if 0.29 < abs(p[0]) < 0.34 and 7.23 < p[1] < 7.35 and p[2] > 1.37
]
dy, dz = (sum(offset[i][axis] for i in eye) / len(eye) for axis in (1, 2))
deltas = []
for point in source:
    dx, y, z = offset.get(index[tuple(point)], (0, 0, 0))
    t = max(0, min(1, (point[1] - 5.86) / 0.62))
    weight = 0.88 * t * t * (3 - 2 * t)
    deltas.append([round(c * weight, 5) for c in (dx, y - dy, z - dz)])
(directory / "camellia-head.json").write_text(
    json.dumps(deltas, separators=(",", ":")) + "\n"
)
