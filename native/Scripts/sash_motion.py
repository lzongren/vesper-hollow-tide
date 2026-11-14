"""Damped travel of the two silk streamers, measured in world centimetres."""

import math
import unreal


class SashMotion:
    def __init__(self):
        self.pawn = self.material = None
        self.offset = unreal.Vector()
        self.rate = unreal.Vector()
        self.yaw = 0.0

    def update(self, pawn, dt):
        yaw = pawn.get_actor_rotation().yaw
        if self.pawn != pawn:
            self.pawn = pawn
            self.yaw = yaw
            self.offset = self.rate = unreal.Vector()
            slot = pawn.mesh.get_material_index("RiverBrocade")
            self.material = (
                pawn.mesh.create_dynamic_material_instance(slot) if slot >= 0 else None
            )
        if self.material is None or dt <= 0:
            return
        dt = min(dt, 0.08)
        turn = (yaw - self.yaw + 180) % 360 - 180
        self.yaw = yaw
        velocity = pawn.get_velocity()
        back = pawn.get_actor_forward_vector() * -1
        across = pawn.get_actor_right_vector()
        speed = min(1, math.hypot(velocity.x, velocity.y) / 450)
        yaw_lag = max(-13, min(13, turn / dt * 0.048))
        # Limit cross-body swing and keep the trailing target behind the belt.
        lateral = max(-12, min(12, -velocity.dot(across) * 0.024))
        target = back * (15 * speed) + across * (yaw_lag + lateral)
        target.z = 8 * speed + 0.28 * abs(yaw_lag)
        steps = math.ceil(dt * 120)
        h = dt / steps
        for _ in range(steps):
            self.rate += ((target - self.offset) * 118 - self.rate * 12.4) * h
            self.offset += self.rate * h
        self.material.set_vector_parameter_value(
            "HemOffsetCm",
            unreal.LinearColor(self.offset.x, self.offset.y, self.offset.z, 0),
        )
