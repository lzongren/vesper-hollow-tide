"""Shared acquisition, animation loading and player lifecycle for the native courts."""

import math
import unreal


def live(obj):
    # The Python wrapper can outlive the UObject during map travel. IsValid
    # rejects such wrappers before the call reaches its C++ implementation.
    try:
        return unreal.SystemLibrary.is_valid(obj)
    except TypeError:
        return False


class CourtEncounter:
    def __init__(self, step):
        self.step = step
        self.actor = None
        self.pc_target = None
        self.state = "waiting"
        self.deadline = 0.0
        self.turn = 0
        self.clips = []
        self.request_at = 0.0

    def acquire(self, pawn):
        found = unreal.GameplayStatics.get_all_actors_with_tag(pawn, self.tag)
        if not found:
            return False
        self.actor = found[0]
        folder = "/Game/Characters/Mannequins/Anims/Unarmed/Attack/"
        self.clips = [
            unreal.load_asset(folder + name)
            for name in ("MM_Attack_01", "MM_Attack_02", "MM_ChargedAttack")
        ]
        return True

    def update(self, dt):
        pawn = self.step.pawn
        if not live(pawn):
            return
        if self.pc_target is not None and self.pc_target is not pawn:
            self.actor = self.pc_target = None
            self.state, self.turn, self.deadline, self.request_at = (
                "waiting",
                0,
                0.0,
                0.0,
            )
        # Death destroys the enemy actor. Avoid passing its stale Python
        # wrapper back into Unreal while the player explores the cleared court.
        if self.state == "defeated":
            return
        if self.actor is None and not self.acquire(pawn):
            return
        if (
            not live(self.actor)
            or self.actor.get_editor_property("Current HP") <= 0
        ):
            self.actor = None
            self.state = "defeated"
            return
        now = unreal.GameplayStatics.get_time_seconds(pawn)
        if pawn.get_editor_property("Current HP") <= 0:
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
        self.fight(pawn, ai, now, offset, distance, dt)
