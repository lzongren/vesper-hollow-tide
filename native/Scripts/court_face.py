"""Drive jaw and brow motion from the live pawn's combat state."""

import math


class CourtFace:
    def __init__(self):
        self.mesh = None
        self.channels = {}
        self.values = {}
        self.applied = {}
        self.clock = 0
        self.enabled = True

    def update(self, pawn, target, dt):
        if not self.enabled:
            return
        mesh = pawn.mesh
        if mesh != self.mesh:
            self.mesh = mesh
            self.channels = {}
            self.values = {}
            self.applied = {}
            if not mesh or not mesh.skeletal_mesh_asset:
                return
            for n in mesh.skeletal_mesh_asset.get_all_morph_target_names():
                for key in ("JawOpen", "Focus"):
                    if str(n).lower().endswith(key.lower()):
                        self.channels[key] = n
        if not self.channels:
            return
        self.clock += dt
        anim = mesh.get_anim_instance()
        montage = anim.get_current_active_montage() if anim else None
        moving = min(1, pawn.get_velocity().length() / 430)
        effort = 0.0
        if montage:
            pos = anim.montage_get_position(montage)
            effort = 0.5 - 0.5 * math.cos(min(1, pos / 0.40) * math.tau)
        breath = 0.5 - 0.5 * math.cos(self.clock * (2.0 + moving))
        goals = {
            "JawOpen": 0.008 + breath * (0.013 + 0.035 * moving) + 0.22 * effort,
            "Focus": (0.23 if target else 0.025) + 0.26 * effort,
        }
        for key, channel in self.channels.items():
            old = self.values.get(key, 0.0)
            value = old + (goals[key] - old) * (-math.expm1(-dt * 12))
            self.values[key] = value
            if abs(value - self.applied.get(key, 0)) >= 0.003:
                mesh.set_morph_target(channel, value)
                self.applied[key] = value
