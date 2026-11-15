"""Photograph one real cast from the follow camera and measure its damage."""

import json
from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step, duel = runtime["step"], runtime["heron"]
started = None
shots = {}
saw_flight = False
evade = "-FanEvade" in unreal.SystemLibrary.get_command_line()
step_at = None
mix_start = None
mix_mode = None


def tick(dt):
    global started, saw_flight, step_at, mix_start, mix_mode
    pawn = step.pawn
    if not runtime["live"](pawn) or not runtime["live"](duel.actor):
        return
    now = unreal.GameplayStatics.get_time_seconds(pawn)
    if started is None:
        pawn.set_actor_location(unreal.Vector(11060, 1630, 108), False, True)
        step.pc.set_control_rotation(unreal.Rotator(pitch=-5, yaw=0))
        duel.deadline = now + (12.8 if evade else 2.8)
        started = now
    # Warm the scene and mixer before the recorded cast. Avoid synchronous
    # screenshot readbacks during the dodge; one end-frame aligns the window
    # capture to this run's mixer output.
    if evade and mix_start is None and now - started > 10.8:
        mix_mode = unreal.SystemLibrary.get_console_variable_int_value(
            "au.NeverDisableSubmixes"
        )
        unreal.SystemLibrary.execute_console_command(
            pawn, "au.NeverDisableSubmixes 1", step.pc
        )
        unreal.AudioMixerLibrary.start_recording_output(pawn, 16.0)
        mix_start = time.perf_counter()
    moved = max((f[3] for f in duel.active), default=0)
    if evade and moved > 340 and step_at is None:
        pawn.add_movement_input(unreal.Vector(0, 1, 0), 1.0)
        if moved > 432 and step.try_step(now):
            step_at = {
                "seconds": round(now - started, 3),
                "travel_cm": round(moved, 1),
                "y": round(pawn.get_actor_location().y, 1),
            }
    if duel.active:
        saw_flight = True
    phase = None
    if duel.state == "windup" and duel.move == 1:
        phase = (
            "opened"
            if duel.deadline - now < 0.19
            else "opening"
            if duel.deadline - now < 0.80
            else None
        )
    elif moved > 500:
        phase = "passing"
    elif moved > 270:
        phase = "spread"
    elif moved > 86:
        phase = "release"
    if phase and phase not in shots:
        shots[phase] = {
            "seconds": round(now - started, 3),
            "travel_cm": round(moved, 2),
            "projectiles": len(duel.active),
        }
        unreal.log("VESPER_FAN_VIEW " + phase)
        if not evade:
            unreal.SystemLibrary.execute_console_command(pawn, "Shot SHOWUI", step.pc)
    if saw_flight and not duel.active:
        saved = Path(
            unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
        )
        result = {
            "views": shots,
            "hp_after_cast": pawn.get_editor_property("Current HP"),
            "player": pawn.mesh.skeletal_mesh_asset.get_name(),
        }
        name = "HeronFanTrial"
        if evade:
            name = "HeronFanEvade"
            result.update(
                step=step_at,
                final_y=round(pawn.get_actor_location().y, 1),
                mix_seconds=time.perf_counter() - mix_start,
            )
            result["end_qpc"] = time.perf_counter()
            unreal.log("VESPER_FAN_END_FRAME")
            unreal.SystemLibrary.execute_console_command(pawn, "Shot SHOWUI", step.pc)
            unreal.AudioMixerLibrary.stop_recording_output(
                pawn,
                unreal.AudioRecordingExportType.WAV_FILE,
                "SilkEvadeMix",
                str(saved),
            )
            unreal.SystemLibrary.execute_console_command(
                pawn, f"au.NeverDisableSubmixes {mix_mode}", step.pc
            )
        (saved / (name + ".json")).write_text(json.dumps(result))
        unreal.log("VESPER_FAN_DONE " + str(result))
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
