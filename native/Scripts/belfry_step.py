"""Short evasive step for the standalone, editor-hosted combat build."""

import unreal


def input_key(name):
    key = unreal.Key()
    key.import_text(name)
    return key


class BelfryStep:
    def __init__(self):
        self.keys = [input_key("SpaceBar"), input_key("Gamepad_FaceButton_Bottom")]
        self.pawn = None
        self.pc = None
        self.was_down = False
        self.next_step = 0.0
        self.restore_at = None
        self.old_damage = True

    def update(self, dt):
        if not unreal.SystemLibrary.is_valid(self.pc):
            self.pc = next(
                (
                    pc
                    for pc in unreal.ObjectIterator(unreal.PlayerController)
                    if pc.is_local_controller() and pc.get_controlled_pawn()
                ),
                None,
            )
        if not unreal.SystemLibrary.is_valid(self.pc):
            return
        pawn = self.pc.get_controlled_pawn()
        if pawn != self.pawn:
            if self.restore_at is not None and unreal.SystemLibrary.is_valid(self.pawn):
                self.pawn.set_editor_property("can_be_damaged", self.old_damage)
            self.pawn, self.restore_at = pawn, None
            self.next_step = 0.0
        if not pawn:
            return
        now = unreal.GameplayStatics.get_time_seconds(pawn)
        if self.restore_at is not None and now >= self.restore_at:
            pawn.set_editor_property("can_be_damaged", self.old_damage)
            self.restore_at = None
        down = any(self.pc.is_input_key_down(k) for k in self.keys)
        if down and not self.was_down:
            self.try_step(now)
        self.was_down = down

    def try_step(self, now):
        pawn = self.pawn
        if (
            not pawn
            or now < self.next_step
            or not pawn.character_movement.is_moving_on_ground()
            or pawn.get_editor_property("Current HP") <= 0
        ):
            return False
        direction = pawn.get_last_movement_input_vector()
        if direction.length() < 0.1:
            direction = pawn.get_actor_forward_vector() * -1.0
        direction = direction.normal()
        self.old_damage = pawn.get_editor_property("can_be_damaged")
        pawn.set_editor_property("can_be_damaged", False)
        pawn.launch_character(direction * 770, True, False)
        self.restore_at = now + 0.22
        self.next_step = now + 0.75
        return True


step = BelfryStep()
handle = unreal.register_slate_post_tick_callback(step.update)
