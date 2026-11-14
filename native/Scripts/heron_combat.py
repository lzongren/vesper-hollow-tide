"""The bride locks a line for her lunge and casts seven moving, dodgeable feathers."""

import math
import unreal


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
        self.active = []
        self.hit = False
        self.sound = unreal.load_asset("/Game/Vesper/Duel/SilkDraw")
        return True

    def update(self, dt):
        super().update(dt)
        if self.state == "defeated" and getattr(self, "active", None):
            for actor, _, _, _ in self.active:
                if live(actor):
                    actor.set_actor_hidden_in_game(True)
            self.active.clear()

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
                if not self.hit:
                    self.hit_player(pawn, ai, 2)
                    self.hit = True
                quill.set_actor_hidden_in_game(True)
            elif advance >= 1250:
                quill.set_actor_hidden_in_game(True)
            else:
                quill.set_actor_location(end, False, True)
                remaining.append((quill, origin, axis, advance))
        self.active = remaining

    def fight(self, pawn, ai, now, offset, distance, dt):
        self.fly(pawn, ai, dt)
        if self.state == "windup":
            if now < self.deadline:
                return
            if self.move == 1:
                origin = self.actor.get_actor_location() + self.axis * 52
                for i, quill in enumerate(self.feathers):
                    angle = self.yaw + (i - (len(self.feathers) - 1) / 2) * 10
                    axis = unreal.Vector(
                        math.cos(math.radians(angle)), math.sin(math.radians(angle)), 0
                    )
                    quill.set_actor_location_and_rotation(
                        origin, unreal.Rotator(yaw=angle), False, True
                    )
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
        windup = (0.63, 1.12, 0.87)[move]
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
