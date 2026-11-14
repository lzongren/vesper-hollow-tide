"""Direct the Bellwarden's path, committed blows and recovery in standalone play."""

import math
import sys
import runpy
from pathlib import Path

import unreal


sys.path.insert(0, str(Path(__file__).parent))
from court_encounter import CourtEncounter, live
from heron_combat import Heron
from cinder_combat import Saint


class Bellwarden(CourtEncounter):
    tag = "Bellwarden"

    def acquire(self, pawn):
        if not super().acquire(pawn):
            return False
        self.tones = [
            unreal.load_asset("/Game/Vesper/Duel/" + name)
            for name in ("BronzeSweep", "GraveToll")
        ]
        return True

    def fight(self, pawn, ai, now, offset, distance, dt):
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
heron = Heron(step)
saint = Saint(step)
fallen_at = None
fallen_pawn = None


def update_encounters(dt):
    global fallen_at, fallen_pawn
    pawn = step.pawn
    if not live(pawn):
        return
    if pawn.get_editor_property("Current HP") <= 0:
        now = unreal.GameplayStatics.get_time_seconds(pawn)
        if fallen_pawn != pawn:
            fallen_pawn, fallen_at = pawn, now + 1.4
            for duel in (boss, heron, saint):
                if (
                    live(duel.actor)
                    and duel.actor.get_controller()
                ):
                    duel.actor.get_controller().stop_movement()
        elif now >= fallen_at:
            # Python actor wrappers outlive the world they wrap. Release them before
            # travel, including the step controller, which is ticked independently.
            for duel in (boss, heron, saint):
                duel.actor = duel.pc_target = None
                duel.state = "waiting"
                duel.turn = duel.deadline = duel.request_at = 0
            saint.clear()
            heron.active = []
            heron.feathers = []
            step.release_world()
            fallen_at = fallen_pawn = None
            unreal.GameplayStatics.open_level(pawn, "MountainPilgrimage")
        return
    fallen_at = fallen_pawn = None
    boss.update(dt)
    heron.update(dt)
    saint.update(dt)


handle = unreal.register_slate_post_tick_callback(update_encounters)
unreal.log("VESPER_BELFRY_COMBAT_ACTIVE")
