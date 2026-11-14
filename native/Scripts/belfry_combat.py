"""Direct the Bellwarden's path, committed blows and recovery in standalone play."""

import math
import runpy
from pathlib import Path

import unreal


class Bellwarden:
    def __init__(self, step):
        self.step = step
        self.actor = None
        self.pc_target = None
        self.state = "waiting"
        self.deadline = 0.0
        self.turn = 0
        self.clips = []
        self.tones = []
        self.request_at = 0.0

    def acquire(self, pawn):
        found = unreal.GameplayStatics.get_all_actors_with_tag(pawn, "Bellwarden")
        if not found:
            return False
        self.actor = found[0]
        folder = "/Game/Characters/Mannequins/Anims/Unarmed/Attack/"
        self.clips = [
            unreal.load_asset(folder + name)
            for name in ("MM_Attack_01", "MM_Attack_02", "MM_ChargedAttack")
        ]
        self.tones = [
            unreal.load_asset("/Game/Vesper/Duel/" + name)
            for name in ("BronzeSweep", "GraveToll")
        ]
        return True

    def update(self, dt):
        pawn = self.step.pawn
        if not unreal.SystemLibrary.is_valid(pawn):
            return
        if self.pc_target is not None and not unreal.SystemLibrary.is_valid(
            self.pc_target
        ):
            self.actor = self.pc_target = None
            self.state, self.turn, self.deadline, self.request_at = (
                "waiting",
                0,
                0.0,
                0.0,
            )
        if self.actor is None and not self.acquire(pawn):
            return
        if (
            not unreal.SystemLibrary.is_valid(self.actor)
            or self.actor.get_editor_property("Current HP") <= 0
        ):
            self.state = "defeated"
            return
        now = unreal.GameplayStatics.get_time_seconds(pawn)
        if pawn.get_editor_property("Current HP") <= 0:
            if self.state != "fallen":
                self.actor.get_controller().stop_movement()
                self.state, self.deadline = "fallen", now + 1.4
            elif now >= self.deadline:
                self.actor = self.pc_target = None
                self.state, self.turn, self.deadline, self.request_at = (
                    "waiting",
                    0,
                    0.0,
                    0.0,
                )
                unreal.GameplayStatics.open_level(pawn, "MountainPilgrimage")
            return
        if pawn != self.pc_target:
            self.pc_target = pawn
            self.actor.get_controller().stop_movement()
            self.state, self.deadline = "waiting", now + 0.8
            return
        offset = pawn.get_actor_location() - self.actor.get_actor_location()
        distance = math.hypot(offset.x, offset.y)
        ai = self.actor.get_controller()
        if not ai:
            return
        if self.state == "windup":
            if now >= self.deadline:
                forward = self.actor.get_actor_forward_vector()
                cosine = (forward.x * offset.x + forward.y * offset.y) / max(
                    distance, 1
                )
                if distance < self.reach and abs(offset.z) < 140 and cosine > self.arc:
                    unreal.GameplayStatics.apply_damage(
                        pawn,
                        self.damage,
                        ai,
                        self.actor,
                        unreal.DamageType.static_class(),
                    )
                self.state, self.deadline = "recovery", now + self.recovery
            return
        if now < self.deadline:
            return
        if distance > 1450 or abs(offset.z) > 190:
            if self.state != "waiting":
                ai.stop_movement()
            self.state = "waiting"
            return
        if distance > 182:
            if now >= self.request_at:
                ai.move_to_actor(pawn, 95, False)
                self.request_at = now + 0.40
            self.state = "approach"
            return
        ai.stop_movement()
        self.actor.set_actor_rotation(
            unreal.Rotator(yaw=math.degrees(math.atan2(offset.y, offset.x))), False
        )
        index = self.turn % 3
        self.turn += 1
        heavy = index == 2
        self.reach, self.arc = (228, 0.55) if heavy else (197, 0.08)
        self.damage = 3 if heavy else 2
        self.recovery = 1.45 if heavy else 0.97
        windup = 1.0 if heavy else 0.51
        anim = self.actor.mesh.get_anim_instance()
        anim.play_slot_animation_as_dynamic_montage(
            self.clips[index], "DefaultSlot", 0.11, 0.22, 0.74 if heavy else 0.86
        )
        unreal.GameplayStatics.play_sound_at_location(
            self.actor,
            self.tones[int(heavy)],
            self.actor.get_actor_location(),
            unreal.Rotator(),
            volume_multiplier=0.76,
            pitch_multiplier=1.0 if heavy else 1.03,
        )
        self.state, self.deadline = "windup", now + windup


step = runpy.run_path(str(Path(__file__).with_name("belfry_step.py")))["step"]
boss = Bellwarden(step)
handle = unreal.register_slate_post_tick_callback(boss.update)
unreal.log("VESPER_BELFRY_COMBAT_ACTIVE")
