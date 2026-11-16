"""Natural blink timing and the fitted eyelid shape of the playable swordswoman."""

import math


def lid_delta(x, y, z):
    """Return the closure displacement in glTF metres for the source head."""
    t = (abs(x) - 0.155) / 0.30
    if not 0 < t < 1 or z < 1.17 or not 7.12 < y < 7.52:
        return (0.0, 0.0, 0.0)
    span = math.sin(math.pi * t) ** 0.88
    centre = 7.266 + 0.026 * t
    upper = y >= centre
    rim = centre + (0.050 if upper else -0.041) * span
    width = 0.075 if upper else 0.044
    falloff = math.exp(-(((y - rim) / width) ** 2))
    front = max(0.0, min(1.0, (z - 1.17) / 0.16))
    amount = span * falloff * front
    return (0.0, (-0.075 if upper else 0.022) * 0.103 * amount, 0.0012 * amount)


def install_shape(
    out, face_slot, vertices, *, closure=lid_delta, attachments=None, displacements=None
):
    mesh = out.doc["meshes"][0]
    shape = out.data(
        displacements if displacements is not None else [closure(*v) for v in vertices],
        "VEC3",
        bounds=True,
    )
    zeros = {}
    for primitive in mesh["primitives"]:
        if primitive["material"] == face_slot:
            delta = shape
        elif attachments and primitive["material"] in attachments:
            delta = attachments[primitive["material"]]
        else:
            count = out.doc["accessors"][primitive["attributes"]["POSITION"]]["count"]
            if count not in zeros:
                zeros[count] = out.data([(0, 0, 0)] * count, "VEC3", bounds=True)
            delta = zeros[count]
        primitive["targets"] = [{"POSITION": delta}]
    mesh["extras"] = dict(targetNames=["Blink"])
    mesh["weights"] = [0.0]


class Blink:
    """Drive the morph on the currently possessed mesh, including after respawn."""

    def __init__(self):
        self.mesh = self.target = self.skin = None
        self.age = self.last = 0.0
        self.index = 0
        self.intervals = (3.38, 4.76, 2.94, 5.31, 3.89)

    def pose(self, weight):
        self.mesh.set_morph_target(self.target, weight)
        if self.skin:
            self.skin.set_scalar_parameter_value("LidClosure", weight)

    def update(self, pawn, dt):
        mesh = pawn.mesh
        if mesh != self.mesh:
            if not mesh or not mesh.skeletal_mesh_asset:
                return
            self.mesh = mesh
            self.skin = None
            slot = mesh.get_material_index("WayfarerSkin")
            names = mesh.skeletal_mesh_asset.get_all_morph_target_names()
            if slot >= 0 and not any(str(n).lower().endswith("jawopen") for n in names):
                self.skin = mesh.create_dynamic_material_instance(slot)
            self.target = next(
                (n for n in names if str(n).lower().endswith("blink")),
                None,
            )
            self.age = self.last = 0.0
            self.index = 0
        if not self.target:
            return
        self.age += dt
        t = self.age - self.intervals[self.index]
        if t < 0:
            return
        if t < 0.073:
            a = t / 0.073
        elif t < 0.097:
            a = 1.0
        elif t < 0.247:
            a = 1 - (t - 0.097) / 0.15
        else:
            a = 0.0
            self.index = (self.index + 1) % len(self.intervals)
            self.age = 0.0
        weight = a * a * (3 - 2 * a)
        if weight != self.last:
            self.pose(weight)
            self.last = weight
