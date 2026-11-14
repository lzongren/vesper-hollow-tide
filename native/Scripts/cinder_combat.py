"""The Saint commits his staff, raises a travelling seal and marks one fixed eruption."""

import math
import unreal
from court_encounter import CourtEncounter, live


class Saint(CourtEncounter):
    tag = "CinderSaint"

    def acquire(self, pawn):
        if not super().acquire(pawn):
            return False
        self.effects = [
            unreal.GameplayStatics.get_all_actors_with_tag(pawn, tag)[0]
            for tag in ("CinderWave", "CinderMark", "CinderFlame")
        ]
        self.tone = unreal.load_asset("/Game/Vesper/Duel/PrayerBell")
        flame = self.effects[2].static_mesh_component
        self.plume = flame.create_dynamic_material_instance(0)
        self.radius = 0
        self.move = -1
        return True

    def clear(self):
        for effect in getattr(self, "effects", []):
            if live(effect):
                effect.set_actor_hidden_in_game(True)
        self.effects = []

    def update(self, dt):
        super().update(dt)
        if self.state == "defeated" and self.effects:
            self.clear()

    def show(self, index, pos, radius, height=1):
        a = self.effects[index]
        a.set_actor_location(pos, False, True)
        a.set_actor_scale3d(unreal.Vector(radius / 100, radius / 100, height))
        a.set_actor_hidden_in_game(False)

    def strike(self, pawn, ai, amount):
        unreal.GameplayStatics.apply_damage(
            pawn, amount, ai, self.actor, unreal.DamageType.static_class()
        )

    def chant(self, pitch, volume):
        unreal.GameplayStatics.play_sound_at_location(
            self.actor,
            self.tone,
            self.actor.get_actor_location(),
            unreal.Rotator(),
            volume_multiplier=volume,
            pitch_multiplier=pitch,
        )

    def fight(self, pawn, ai, now, offset, distance, dt):
        if self.state == "windup":
            if now < self.deadline:
                return
            if self.move == 1:
                self.state, self.began = "wave", now
                self.radius = 62
                return
            if self.move == 2:
                self.effects[1].set_actor_hidden_in_game(True)
                self.plume.set_vector_parameter_value(
                    "FrameUV", unreal.LinearColor(0, 0, 0, 0)
                )
                self.show(2, self.origin, 117, 1)

                self.state, self.began = "eruption", now
                self.chant(0.62, 0.72)
                return
            if (
                distance < 250
                and abs(offset.z) < 150
                and self.axis.dot(offset) / max(1, distance) > 0.08
            ):
                self.strike(pawn, ai, 3)
            self.state, self.deadline = "recovery", now + 1.03
            return
        if self.state == "wave":
            previous = self.radius
            self.radius = min(1130, 62 + (now - self.began) * 685)
            self.show(0, self.origin, self.radius)
            delta = pawn.get_actor_location() - self.origin
            dist = math.hypot(delta.x, delta.y)
            if (
                not self.hit
                and previous - 28 <= dist <= self.radius + 28
                and abs(delta.z) < 168
            ):
                self.strike(pawn, ai, 2)
                self.hit = True
            if self.radius >= 1130:
                self.effects[0].set_actor_hidden_in_game(True)
                self.state, self.deadline = "recovery", now + 1.15
            return
        if self.state == "eruption":
            t = min(1, (now - self.began) / 0.93)
            frame = min(15, int(t * 16))
            self.plume.set_vector_parameter_value(
                "FrameUV", unreal.LinearColor((frame % 4) / 4, (frame // 4) / 4, 0, 0)
            )
            camera = (
                self.step.pc.player_camera_manager.get_camera_location() - self.origin
            )
            self.effects[2].set_actor_rotation(
                unreal.Rotator(yaw=math.degrees(math.atan2(camera.y, camera.x)) - 90),
                False,
            )
            delta = pawn.get_actor_location() - self.origin
            if (
                not self.hit
                and t < 0.30
                and math.hypot(delta.x, delta.y) < 144
                and abs(delta.z) < 212
            ):
                self.strike(pawn, ai, 3)
                self.hit = True
            if t >= 1:
                self.effects[2].set_actor_hidden_in_game(True)
                self.state, self.deadline = "recovery", now + 1.50
            return
        if now < self.deadline:
            return
        if distance > 1450 or abs(offset.z) > 190:
            if self.state != "waiting":
                ai.stop_movement()
            self.state = "waiting"
            return
        move = (2, 1, 0)[self.turn % 3]
        if distance > (203, 920, 1040)[move]:
            if now >= self.request_at:
                ai.move_to_actor(pawn, 88, False)
                self.request_at = now + 0.38
            self.state = "approach"
            return
        ai.stop_movement()
        self.actor.set_actor_rotation(
            unreal.Rotator(yaw=math.degrees(math.atan2(offset.y, offset.x))), False
        )
        self.axis = self.actor.get_actor_forward_vector()
        self.turn += 1
        self.move, self.hit = move, False
        if move:
            pos = (
                pawn.get_actor_location()
                if move == 2
                else self.actor.get_actor_location()
            )
            # The reliquary's stone deck is level. The inscription stays at the
            # committed position while the player steps out of its footprint.
            self.origin = unreal.Vector(pos.x, pos.y, 14)
            self.radius = 144 if move == 2 else 62
            self.show(1 if move == 2 else 0, self.origin, self.radius)
        self.actor.mesh.get_anim_instance().play_slot_animation_as_dynamic_montage(
            self.clips[(1, 2, 0)[move]],
            "DefaultSlot",
            0.14,
            0.26,
            (0.74, 0.59, 0.71)[move],
        )
        self.chant((1.08, 0.74, 0.91)[move], 0.61)
        self.state, self.deadline = "windup", now + (0.84, 1.35, 1.43)[move]
