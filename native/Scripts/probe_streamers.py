"""Drive a short run, change of direction and stop on the belfry approach."""

import json
import math
from pathlib import Path
import runpy
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
start = camera = None
rows = []
next_sample = 0
shots = [(2.0, "rest"), (5.45, "run"), (6.25, "turn"), (10.8, "settled")]


def tick(_dt):
    global start, camera, next_sample
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    now = unreal.GameplayStatics.get_time_seconds(pawn)
    if start is None:
        pawn.set_actor_location(unreal.Vector(700, 0, 110), False, True)
        pawn.set_actor_rotation(unreal.Rotator(yaw=0), False)
        step.pc.set_control_rotation(unreal.Rotator(yaw=0))
        camera = pawn.get_component_by_class(unreal.CameraComponent)
        camera.set_absolute(True, True, False)
        camera.set_editor_property("use_pawn_control_rotation", False)
        start = now
    t = now - start
    if 3.0 < t < 8.2:
        angle = math.radians(65 * max(0, min(1, (t - 5.6) / 0.50)))
        step.pc.set_control_rotation(unreal.Rotator(yaw=math.degrees(angle)))
        pawn.add_movement_input(unreal.Vector(math.cos(angle), math.sin(angle), 0), 1)
    pos = pawn.get_actor_location()
    loc = pos + unreal.Vector(-275, -97, 43)
    aim = pos + unreal.Vector(0, 0, 6)
    camera.set_world_location_and_rotation(
        loc, unreal.MathLibrary.find_look_at_rotation(loc, aim), False, True
    )
    camera.set_field_of_view(43)
    sash = runtime["sash"]
    if t >= next_sample and sash.material:
        d = sash.material.get_vector_parameter_value("HemOffsetCm")
        rows.append(
            [
                round(t, 3),
                round(pawn.get_velocity().length(), 1),
                round(pawn.get_actor_rotation().yaw, 1),
                round(d.r, 2),
                round(d.g, 2),
                round(d.b, 2),
            ]
        )
        next_sample = t + 0.05
    if shots and t >= shots[0][0]:
        unreal.log("VESPER_STREAMER_VIEW " + shots.pop(0)[1])
        unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    if t > 12:
        output = (
            Path(
                unreal.Paths.convert_relative_path_to_full(
                    unreal.Paths.project_saved_dir()
                )
            )
            / "Streamers.json"
        )
        output.write_text(
            json.dumps(
                dict(
                    mesh=pawn.mesh.skeletal_mesh_asset.get_name(),
                    columns=[
                        "seconds",
                        "speed_cm_s",
                        "yaw_deg",
                        "hem_x_cm",
                        "hem_y_cm",
                        "hem_z_cm",
                    ],
                    samples=rows,
                )
            )
        )
        unreal.log("VESPER_STREAMERS_DONE")
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
