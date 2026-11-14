"""Walk the complete mountain route and fight each boss using the possessed pawn."""

import json
import math
from pathlib import Path
import runpy
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
duels = [runtime[k] for k in ("boss", "heron", "saint")]
stages = [
    (4200, 0, 0),
    (7600, 1600, None),
    (11500, 1600, 1),
    # Leave the moon gate along the diagonal causeway, inside its gatepost.
    (11950, 1273, None),
    (13200, 364, None),
    (14800, -800, None),
    (19400, -800, 2),
]
stage = 0
rows = []
wins = []
start = last_sample = original = None
last_attack = -1.0
pressed = False
saved = Path(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
)


def finish(reason):
    (saved / "ThreeCourtTrial.json").write_text(
        json.dumps(
            dict(
                outcome=reason,
                columns=[
                    "seconds",
                    "stage",
                    "x",
                    "y",
                    "player_hp",
                    "boss_hp",
                    "boss_state",
                ],
                samples=rows,
                victories=wins,
            )
        )
    )
    unreal.log("VESPER_THREE_COURTS " + reason)
    unreal.unregister_slate_post_tick_callback(handle)


def tick(dt):
    global stage, start, original, last_sample, last_attack, pressed
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    if start is None:
        start = unreal.GameplayStatics.get_time_seconds(pawn)
        original = pawn
        last_sample = -1
    if pawn is not original:
        return finish("respawned")
    now = unreal.GameplayStatics.get_time_seconds(pawn)
    t = now - start
    pos = pawn.get_actor_location()
    if stage >= len(stages):
        return finish("cleared")
    x, y, i = stages[stage]
    hp = pawn.get_editor_property("Current HP")
    if t > 290:
        return finish("timeout")
    pc = step.pc
    if pressed and now - last_attack > 0.14:
        unreal.SystemLibrary.execute_console_command(
            pawn, "Input.-key LeftMouseButton", pc
        )
        pressed = False
    duel = duels[i] if i is not None else None
    if duel and duel.state == "defeated":
        wins.append([duel.tag, round(t, 3), hp])
        stage += 1
        return
    bhp = None
    if duel and runtime["live"](duel.actor):
        target = duel.actor.get_actor_location()
        x, y = target.x, target.y
        bhp = duel.actor.get_editor_property("Current HP")
    dx, dy = x - pos.x, y - pos.y
    distance = math.hypot(dx, dy)
    if now - last_sample > 0.24:
        rows.append(
            [
                round(t, 2),
                stage,
                round(pos.x),
                round(pos.y),
                hp,
                bhp,
                duel.state if duel else "travel",
            ]
        )
        if len(rows) % 20 == 0:
            unreal.log("VESPER_ROUTE_SAMPLE " + str(rows[-1]))
        last_sample = now
    if not duel and distance < 100:
        stage += 1
        return
    if hp <= 0:
        return
    if distance > 1:
        yaw = math.degrees(math.atan2(dy, dx))
        pc.set_control_rotation(unreal.Rotator(pitch=-8, yaw=yaw))
        pawn.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
    if distance > 95:
        pawn.add_movement_input(unreal.Vector(dx / distance, dy / distance, 0), 1)
    if not duel or distance > 235:
        return
    if duel.state == "windup" and 0 < duel.deadline - now < 0.13:
        step.try_step(now)
    if now - last_attack > 0.54:
        unreal.SystemLibrary.execute_console_command(
            pawn, "Input.+key LeftMouseButton 1", pc
        )
        pressed = True
        last_attack = now


def safe(dt):
    try:
        tick(dt)
    except Exception as e:
        unreal.log_error("THREE_COURTS_ERROR " + repr(e))
        finish("error")


handle = unreal.register_slate_post_tick_callback(safe)
