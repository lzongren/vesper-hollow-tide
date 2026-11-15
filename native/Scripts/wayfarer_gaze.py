"""Aim the iris pigment in the animated head's frame of reference."""

import math

import unreal

from court_encounter import live


def head_axes(pawn):
    """Express the rest-pose face axes in head-bone space once per possession."""
    mesh = pawn.mesh
    mathlib = unreal.MathLibrary
    bone = "head"
    ref = unreal.Transform()
    while mesh.get_bone_index(bone) >= 0:
        local = mesh.get_ref_pose_transform(mesh.get_bone_index(bone))
        ref = mathlib.compose_transforms(ref, local)
        bone = mesh.get_parent_bone(bone)
    component = mesh.get_world_transform()
    return tuple(
        mathlib.inverse_transform_direction(
            ref, mathlib.inverse_transform_direction(component, axis)
        )
        for axis in (
            pawn.get_actor_forward_vector(),
            pawn.get_actor_right_vector(),
            pawn.get_actor_up_vector(),
        )
    )


class Gaze:
    def __init__(self):
        self.clear()

    def clear(self):
        self.pawn = self.material = self.target = None
        self.angles = (0.0, 0.0)
        self.next_check = 0.0

    def update(self, pawn, pc, duels, dt):
        mesh = pawn.mesh
        if self.pawn != pawn:
            self.clear()
            self.pawn = pawn
            slot = mesh.get_material_index("WetIris")
            if slot >= 0 and mesh.get_bone_index("head") >= 0:
                self.axes = head_axes(pawn)
                self.material = mesh.create_dynamic_material_instance(slot)
        if not self.material:
            return
        now = unreal.GameplayStatics.get_time_seconds(pawn)
        head = mesh.get_socket_transform("head")
        fwd, right, up = (
            unreal.MathLibrary.transform_direction(head, a) for a in self.axes
        )
        eye = head.translation + fwd * 9 + up * 6
        if now >= self.next_check:
            options = []
            for duel in duels:
                actor = duel.actor
                if not live(actor) or duel.state == "defeated":
                    continue
                ray = actor.get_actor_location() - eye
                dist = ray.length()
                if dist > 1450 or fwd.dot(ray) < dist * 0.35:
                    continue
                if pc.line_of_sight_to(actor, eye):
                    options.append((dist * (0.8 if actor == self.target else 1), actor))
            self.target = min(options, key=lambda item: item[0])[1] if options else None
            self.next_check = now + 0.10
        yaw = pitch = 0.0
        if live(self.target):
            aim = self.target.mesh.get_socket_location("head")
            ray = aim - eye
            z, x, y = ray.dot(up), ray.dot(fwd), ray.dot(right)
            if x > 0:
                yaw = max(-0.27, min(0.27, math.atan2(y, x)))
                pitch = max(-0.16, min(0.13, math.atan2(z, math.hypot(x, y))))
        # A short, frame-rate-independent saccade settles on the opponent.
        gain = -math.expm1(-28 * max(0, dt))
        a, b = self.angles
        self.angles = (a + (yaw - a) * gain, b + (pitch - b) * gain)
        if max(abs(self.angles[0] - a), abs(self.angles[1] - b)) > 1e-7:
            # Positive glTF X is the swordswoman's left, positive Y is up.
            self.material.set_vector_parameter_value(
                "IrisDirection",
                unreal.LinearColor(
                    -math.sin(self.angles[0]), math.sin(self.angles[1]), 0, 0
                ),
            )
