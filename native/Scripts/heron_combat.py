"""The bride locks a line for her lunge and casts seven moving, dodgeable feathers."""

import math
import unreal


from heron_fan import CAST_SECONDS, flight_rotation, heading, unfold
from court_encounter import CourtEncounter, live


class Heron(CourtEncounter):
    tag = "VeiledHeron"

    def acquire(self, pawn):
        if not super().acquire(pawn):
            return False
        self.feathers = sorted(
            unreal.GameplayStatics.get_all_actors_with_tag(pawn, "HeronQuill"),
            key=lambda a: a.get_name(),
        )
        self.lanes = {
            a: i - (len(self.feathers) - 1) / 2 for i, a in enumerate(self.feathers)
        }
        self.wakes = {}
        for quill in self.feathers:
            comp = quill.static_mesh_component
            slot = comp.get_material_index("VaneSlipstream")
            if slot >= 0:
                self.wakes[quill] = comp.create_dynamic_material_instance(slot)
        self.active = []
        self.hit = self.volley_hit = False
        self.release_sound = unreal.load_asset(
            "/Game/Vesper/Duel/HeronFlightArt/VaneRelease"
        )
        self.sound = unreal.load_asset("/Game/Vesper/Duel/SilkDraw")
        for cue in (self.sound, self.release_sound):
            if cue:
                unreal.GameplayStatics.prime_sound(cue)
        return True

    def update(self, dt):
        super().update(dt)
        if self.state == "defeated" and getattr(self, "feathers", None):
            self.clear_cast()

    def clear_cast(self):
        for actor in getattr(self, "feathers", ()):
            if live(actor):
                actor.set_actor_hidden_in_game(True)
        self.feathers, self.active = [], []
        self.wakes, self.lanes = {}, {}

    def hit_player(self, pawn, ai, damage):
        unreal.GameplayStatics.apply_damage(
            pawn, damage, ai, self.actor, unreal.DamageType.static_class()
        )

    def fly(self, pawn, ai, dt):
        remaining = []
        target = pawn.get_actor_location()
        for quill, origin, axis, travelled in self.active:
            advance = min(1250, travelled + dt * 735)
            start = origin + axis * travelled
            end = origin + axis * advance
            along = max(0, min(advance - travelled, (target - start).dot(axis)))
            if (target - (start + axis * along)).length() < 52:
                if not self.volley_hit:
                    self.hit_player(pawn, ai, 2)
                    self.volley_hit = True
                quill.set_actor_hidden_in_game(True)
            elif advance >= 1250:
                quill.set_actor_hidden_in_game(True)
            else:
                wake = self.wakes.get(quill)
                if wake:
                    wake.set_scalar_parameter_value(
                        "Flight", min(1, advance / 85, (1250 - advance) / 115)
                    )
                lane = self.lanes[quill]
                quill.set_actor_location_and_rotation(
                    end,
                    flight_rotation(
                        math.degrees(math.atan2(axis.y, axis.x)), lane, advance
                    ),
                    False,
                    True,
                )
                remaining.append((quill, origin, axis, advance))
        self.active = remaining

    def fight(self, pawn, ai, now, offset, distance, dt):
        self.fly(pawn, ai, dt)
        if self.state == "windup":
            if now < self.deadline:
                if self.move == 1:
                    unfold(self, now)
                return
            if self.move == 1:
                self.volley_hit = False
                origin = self.actor.get_actor_location() + self.axis * 52
                if self.release_sound:
                    unreal.GameplayStatics.play_sound_at_location(
                        pawn,
                        self.release_sound,
                        origin,
                        unreal.Rotator(),
                        volume_multiplier=0.82,
                    )
                for quill in self.feathers:
                    angle = self.yaw + self.lanes[quill] * 10
                    axis = heading(angle)
                    quill.set_actor_location_and_rotation(
                        origin,
                        flight_rotation(angle, self.lanes[quill], 0),
                        False,
                        True,
                    )
                    quill.set_actor_scale3d(unreal.Vector(1, 1, 1))
                    quill.set_actor_hidden_in_game(False)
                    self.active.append((quill, origin, axis, 0))
            elif self.move == 2:
                self.state, self.deadline = "lunge", now + 0.38
                self.actor.launch_character(self.axis * 970, True, False)
                return
            elif (
                distance < 230
                and abs(offset.z) < 140
                and self.axis.dot(offset) / max(1, distance) > 0.18
            ):
                self.hit_player(pawn, ai, 2)
            self.state, self.deadline = (
                "recovery",
                now + (1.35 if self.move == 1 else 0.88),
            )
            return
        if self.state == "lunge":
            if distance < 155 and abs(offset.z) < 140 and not self.hit:
                self.hit_player(pawn, ai, 3)
                self.hit = True
            if now >= self.deadline:
                self.actor.character_movement.stop_movement_immediately()
                self.state, self.deadline = "recovery", now + 1.12
            return
        if now < self.deadline:
            return
        if distance > 1430 or abs(offset.z) > 180:
            if self.state != "waiting":
                ai.stop_movement()
            self.state = "waiting"
            return
        move = (1, 2, 0, 0)[self.turn % 4]
        reach = (184, 830, 555)[move]
        if distance > reach:
            if now >= self.request_at:
                ai.move_to_actor(pawn, 82, False)
                self.request_at = now + 0.35
            self.state = "approach"
            return
        ai.stop_movement()
        self.yaw = math.degrees(math.atan2(offset.y, offset.x))
        self.actor.set_actor_rotation(unreal.Rotator(yaw=self.yaw), False)
        self.axis = self.actor.get_actor_forward_vector()
        self.move, self.hit = move, False
        self.turn += 1
        if move == 1:
            for wake in self.wakes.values():
                wake.set_scalar_parameter_value("Flight", 0.0)
        windup = (0.63, CAST_SECONDS, 0.87)[move]
        self.actor.mesh.get_anim_instance().play_slot_animation_as_dynamic_montage(
            self.clips[(self.turn % 2, 2, 1)[move]],
            "DefaultSlot",
            0.12,
            0.19,
            (0.87, 0.64, 0.76)[move],
        )
        unreal.GameplayStatics.play_sound_at_location(
            self.actor,
            self.sound,
            self.actor.get_actor_location(),
            unreal.Rotator(),
            volume_multiplier=0.7,
            pitch_multiplier=(1.13, 0.81, 0.99)[move],
        )
        self.state, self.deadline = "windup", now + windup
