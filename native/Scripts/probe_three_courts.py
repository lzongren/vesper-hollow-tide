"""Walk the complete mountain route and fight each boss using the possessed pawn."""

import json
import math
from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
duels = [runtime[k] for k in ("boss", "heron", "saint")]
stages = [
    (4200, 0, 0),
    # Follow the centre of the roofed court past the end of the egret wall
    # before turning onto the diagonal road to the moon gate.
    (4890, 55, None),
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
frame_intervals = []
previous_frame = None
player_mesh = None
wins = []
review = "-CourtHUDReview" in unreal.SystemLibrary.get_command_line()
captured = set()
record_mix = "-RecordCourtMix" in unreal.SystemLibrary.get_command_line()
mix_started = None
previous_submix_mode = None
start = last_sample = original = None
last_attack = -1.0
pressed = False
last_contact = None
contact_time = back_off_until = 0.0
saved = Path(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
)


def finish(reason):
    if not review and runtime["live"](step.pc):
        unreal.SystemLibrary.execute_console_command(
            step.pc, "CsvProfile STOP", step.pc
        )
    times = sorted(frame_intervals)

    def percentile(p):
        return round(times[math.ceil(p * len(times)) - 1], 2) if times else None

    (saved / "ThreeCourtTrial.json").write_text(
        json.dumps(
            dict(
                outcome=reason,
                player_mesh=player_mesh,
                callback_intervals_ms=dict(
                    frames=len(times),
                    median=percentile(0.50),
                    p95=percentile(0.95),
                    p99=percentile(0.99),
                    maximum=round(times[-1], 2) if times else None,
                    over_33ms=sum(t > 1000 / 30 for t in times),
                ),
                columns=[
                    "seconds",
                    "stage",
                    "x",
                    "y",
                    "player_hp",
                    "boss_hp",
                    "boss_state",
                    "gaze_target",
                    "gaze_yaw_deg",
                    "gaze_pitch_deg",
                ],
                samples=rows,
                victories=wins,
            )
        )
    )
    if mix_started is not None:
        unreal.AudioMixerLibrary.stop_recording_output(
            step.pc,
            unreal.AudioRecordingExportType.WAV_FILE,
            "ThreeCourtsMix",
            str(saved),
        )
        unreal.SystemLibrary.execute_console_command(
            step.pc, f"au.NeverDisableSubmixes {previous_submix_mode}", step.pc
        )
        unreal.log(f"VESPER_MIX_END {time.perf_counter() - mix_started:.6f}")
    unreal.log("VESPER_THREE_COURTS " + reason)
    unreal.unregister_slate_post_tick_callback(handle)


def tick(dt):
    global stage, start, original, last_sample, last_attack, pressed
    global player_mesh, previous_frame, mix_started, previous_submix_mode
    global last_contact, contact_time, back_off_until
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    wall_time = time.perf_counter()
    if previous_frame is not None:
        frame_intervals.append((wall_time - previous_frame) * 1000)
    previous_frame = wall_time
    if start is None:
        player_mesh = pawn.mesh.skeletal_mesh_asset.get_name()
        if record_mix:
            previous_submix_mode = unreal.SystemLibrary.get_console_variable_int_value(
                "au.NeverDisableSubmixes"
            )
            # The wave writer otherwise omits the silent sections between fights.
            unreal.SystemLibrary.execute_console_command(
                pawn, "au.NeverDisableSubmixes 1", step.pc
            )
            unreal.AudioMixerLibrary.start_recording_output(pawn, 130.0)
            mix_started = time.perf_counter()
        if not review:
            unreal.SystemLibrary.execute_console_command(
                pawn, "CsvProfile START", step.pc
            )
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
    if review:
        hud = runtime["hud"]
        name = None
        if t > 2 and not captured:
            name = "approach"
        elif (
            duel
            and hud.current is duel
            and bhp
            and bhp < duel.actor.get_editor_property("Max HP") - 2
            and abs(hud.boss.last * duel.actor.get_editor_property("Max HP") - bhp)
            < 0.001
        ):
            name = duel.tag
        if name and name not in captured:
            captured.add(name)
            if mix_started is not None:
                unreal.log(
                    f"VESPER_MIX_MARK {name} {time.perf_counter() - mix_started:.6f}"
                )
            unreal.log(
                "VESPER_LIFEBAR_VIEW "
                + name
                + " "
                + str((hp, bhp, hud.player.last, hud.boss.last))
            )
            unreal.SystemLibrary.execute_console_command(pawn, "Shot SHOWUI", pc)
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
                next(
                    (d.tag for d in duels if d.actor is not None and d.actor == runtime["gaze"].target),
                    None,
                ),
                *[round(math.degrees(a), 2) for a in runtime["gaze"].angles],
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
    if duel and bhp is not None:
        contact = (duel.tag, bhp)
        if contact != last_contact or distance > 235:
            last_contact, contact_time = contact, now
        elif now - contact_time > 5.0:
            # A shoulder-to-shoulder orbit can leave the blade outside its target.
            # Use normal movement to make space and approach again.
            contact_time, back_off_until = now, now + 0.55
            unreal.log(f"VESPER_MELEE_REPOSITION {duel.tag} range={distance:.1f} dz={target.z - pos.z:.1f}")
        if now < back_off_until:
            back = pawn.get_actor_forward_vector() * -0.9
            side = pawn.get_actor_right_vector() * 0.35
            pawn.add_movement_input(back + side, 1)
            return
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
