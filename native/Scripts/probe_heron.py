"""Optional 1440p gameplay probe. Run in place of belfry_combat.py with -game."""

import json
import math
from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
live = runtime["live"]
step = runtime["step"]
duel = runtime["heron"]
saved = Path(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
)
rows = []
frame_ms = []
quill_shot = False
shots = [1.0, 3.4, 5.6, 8.6, 13.0, 19.0, 26.0, 33.0]
start = None
last_sample = last_attack = -1
pressed = False
observe_defeat = "-HeronDefeatTrial" in unreal.SystemLibrary.get_command_line()
original = None


def tick(dt):
    global start, last_sample, last_attack, pressed, original, quill_shot
    pawn = step.pawn
    if not live(pawn):
        return
    pc = step.pc
    if start is None:
        if not live(duel.actor):
            return
        start = time.monotonic() + 3
        original = pawn
        pawn.set_actor_location(unreal.Vector(11190, 1645, 105), False, True)
        pc.set_control_rotation(unreal.Rotator(pitch=-5, yaw=-2))
        duel.deadline = unreal.GameplayStatics.get_time_seconds(pawn) + 5.5
    t = time.monotonic() - start
    if t < 0:
        return
    now = unreal.GameplayStatics.get_time_seconds(pawn)
    hp = pawn.get_editor_property("Current HP")
    if t > 2 and duel.state != "defeated":
        frame_ms.append(round(dt * 1000, 3))
    boss = duel.actor
    valid = live(boss)
    bhp = boss.get_editor_property("Current HP") if valid else 0
    if valid and original is pawn and hp > 0:
        offset = boss.get_actor_location() - pawn.get_actor_location()
        distance = math.hypot(offset.x, offset.y)
        if t > 3:
            yaw = math.degrees(math.atan2(offset.y, offset.x))
            pc.set_control_rotation(unreal.Rotator(pitch=-7, yaw=yaw))
            pawn.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
            if not observe_defeat and t > 6:
                if distance > 94:
                    pawn.add_movement_input(
                        unreal.Vector(offset.x / distance, offset.y / distance, 0), 1
                    )
                if duel.state == "windup" and 0 < duel.deadline - now < 0.13:
                    step.try_step(now)
                if pressed and t - last_attack > 0.14:
                    unreal.SystemLibrary.execute_console_command(
                        pawn, "Input.-key LeftMouseButton", pc
                    )
                    pressed = False
                if t - last_attack > 0.52:
                    unreal.SystemLibrary.execute_console_command(
                        pawn, "Input.+key LeftMouseButton 1", pc
                    )
                    pressed = True
                    last_attack = t
    if t - last_sample > 0.12 or pawn is not original:
        last_sample = t
        rows.append(
            [
                round(t, 2),
                hp,
                bhp,
                duel.state,
                getattr(duel, "move", -1),
                len(getattr(duel, "active", [])),
                round(pawn.get_actor_location().x),
            ]
        )
    if not quill_shot and getattr(duel, "active", None) and duel.active[0][3] > 225:
        quill_shot = True
        unreal.SystemLibrary.execute_console_command(pawn, "Shot", pc)
    elif shots and t >= shots[0]:
        shots.pop(0)
        unreal.SystemLibrary.execute_console_command(pawn, "Shot", pc)
    if t >= 49 or pawn is not original:
        log = "HeronDefeatTrial" if observe_defeat else "HeronVictoryTrial"
        (saved / (log + ".json")).write_text(
            json.dumps(
                dict(
                    columns=[
                        "seconds",
                        "player_hp",
                        "boss_hp",
                        "state",
                        "move",
                        "flying_feathers",
                        "player_x",
                    ],
                    samples=rows,
                    frame_ms=frame_ms,
                    respawned=pawn is not original,
                )
            )
        )
        unreal.log("VESPER_HERON_TRIAL " + log + " " + str(rows[-1]))
        unreal.unregister_slate_post_tick_callback(handle)


def safe(dt):
    try:
        tick(dt)
    except Exception as exc:
        unreal.log_error("HERON_TRIAL_ERROR " + repr(exc))
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(safe)
