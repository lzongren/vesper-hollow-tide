"""Walk the real player down the shrine stair and record the live ravine mix."""

from pathlib import Path
import json
import math
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
saved = Path(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
)
points = [(19400, -4570), (19845, -4450)]
profile = "-ProfileRavine" in unreal.SystemLibrary.get_command_line()
start = None
target_index = 0
marks = [5.5, 11.5, 16.5]
samples = []
last_sample = -1
previous_submix = 0


def tick(dt):
    global start, target_index, last_sample, previous_submix
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    pc = step.pc
    if start is None:
        start = time.perf_counter()
        hit = unreal.SystemLibrary.line_trace_single(
            pawn,
            unreal.Vector(19400, -3530, 1300),
            unreal.Vector(19400, -3530, -1400),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True,
            [pawn],
            unreal.DrawDebugTrace.NONE,
            True,
        )
        if not hit:
            raise RuntimeError("Missing shrine stair")
        base = hit.to_tuple()[4]
        pos = unreal.Vector(
            base.x,
            base.y,
            base.z + pawn.capsule_component.get_scaled_capsule_half_height() + 3,
        )
        pawn.set_actor_location_and_rotation(pos, unreal.Rotator(yaw=-90), False, True)
        # The review camera moves independently on the spring arm. Keep the
        # review listener at the walker while the camera circles the inscription.
        pc.set_audio_listener_override(
            pawn.capsule_component, unreal.Vector(0, 0, 60), unreal.Rotator()
        )
        if profile:
            unreal.SystemLibrary.execute_console_command(pawn, "CsvProfile START", pc)
        else:
            previous_submix = unreal.SystemLibrary.get_console_variable_int_value(
                "au.NeverDisableSubmixes"
            )
            unreal.SystemLibrary.execute_console_command(
                pawn, "au.NeverDisableSubmixes 1", pc
            )
            unreal.AudioMixerLibrary.start_recording_output(pawn, 26)
        unreal.log("VESPER_RAVINE_WALK " + pawn.mesh.skeletal_mesh_asset.get_name())
    t = time.perf_counter() - start
    pos = pawn.get_actor_location()
    if t > 2.5 and target_index < len(points):
        dx, dy = points[target_index][0] - pos.x, points[target_index][1] - pos.y
        distance = math.hypot(dx, dy)
        if distance < 35:
            target_index += 1
        else:
            pawn.add_movement_input(
                unreal.Vector(dx / distance, dy / distance, 0), 0.52
            )
            pc.set_control_rotation(
                unreal.Rotator(yaw=math.degrees(math.atan2(dy, dx)))
            )
    # Shoulder camera opens up towards the inscription as the stair levels.
    blend = max(0, min(1, (t - 6) / 9))
    blend = blend * blend * (3 - 2 * blend)
    cam = pawn.get_component_by_class(unreal.CameraComponent)
    cam.set_absolute(True, True, False)
    cam.set_editor_property("use_pawn_control_rotation", False)
    loc = pos + unreal.Vector(-130 - 125 * blend, 355 + 55 * blend, 100 - 25 * blend)
    aim = unreal.Vector(
        pos.x * 0.72 + 20100 * 0.28, pos.y * 0.72 - 4900 * 0.28, pos.z + 33
    )
    cam.set_world_location_and_rotation(
        loc, unreal.MathLibrary.find_look_at_rotation(loc, aim), False, True
    )
    cam.set_field_of_view(61 - 6 * blend)
    if int(t) != last_sample:
        samples.append(
            [round(t, 3), round(pos.x), round(pos.y), round(pos.z), target_index]
        )
        last_sample = int(t)
    if not profile and marks and t >= marks[0]:
        marks.pop(0)
        winds = unreal.GameplayStatics.get_all_actors_of_class(
            pawn, unreal.AmbientSound
        )
        source = next(
            a for a in winds if a.get_actor_label() == "Wind in the ravine grass"
        )
        unreal.log(
            "VESPER_RAVINE_SOURCE "
            + str(source.audio_component.is_playing())
            + " "
            + str(source.get_actor_location())
            + " "
            + source.audio_component.sound.get_name()
        )
        unreal.log("VESPER_RAVINE_FRAME " + str(t))
        unreal.SystemLibrary.execute_console_command(pawn, "Shot", pc)
    if t >= 22:
        if profile:
            unreal.SystemLibrary.execute_console_command(pawn, "CsvProfile STOP", pc)
        else:
            unreal.AudioMixerLibrary.stop_recording_output(
                pc,
                unreal.AudioRecordingExportType.WAV_FILE,
                "RavineGameMix",
                str(saved),
            )
            unreal.SystemLibrary.execute_console_command(
                pc, f"au.NeverDisableSubmixes {previous_submix}", pc
            )
        pc.clear_audio_listener_override()
        result = {
            "mesh": pawn.mesh.skeletal_mesh_asset.get_name(),
            "reached": target_index,
            "elapsed": t,
            "samples": samples,
        }
        (saved / ("RavineTiming.json" if profile else "RavineWalk.json")).write_text(
            json.dumps(result)
        )
        unreal.log("VESPER_RAVINE_WALK_END " + str(target_index))
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
