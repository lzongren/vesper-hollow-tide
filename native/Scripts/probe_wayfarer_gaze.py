"""Matched views while the actual Bellwarden crosses the player's field of view."""

import json
import math
from pathlib import Path
import runpy
import time

import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
cases = [
    ("neutral", -620, 0),
    ("left", 610, -295),
    ("right", 610, 295),
    ("released", -620, 0),
]
started = None
index = 0
samples = []


def tick(dt):
    global index, started
    pawn, keeper = step.pawn, runtime["boss"].actor
    if not runtime["live"](pawn) or not runtime["live"](keeper):
        return
    if started is None:
        pawn.set_actor_location(unreal.Vector(1670, 30, 110), False, True)
        keeper.character_movement.disable_movement()
        started = time.monotonic()
    yaw = 222
    pawn.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
    step.pc.set_control_rotation(unreal.Rotator(yaw=yaw))
    pos = pawn.get_actor_location()
    elapsed = time.monotonic() - started
    moving = index == len(cases)
    if moving:
        name, ahead = "crossing", 610
        across = 295 * math.sin(elapsed * math.tau / 6.2)
    else:
        name, ahead, across = cases[index]
    keeper.set_actor_location(
        pos
        + pawn.get_actor_forward_vector() * ahead
        + pawn.get_actor_right_vector() * across,
        False,
        True,
    )
    az = math.radians(yaw - 10)
    cam = pawn.get_component_by_class(unreal.CameraComponent)
    cam.set_absolute(True, True, False)
    cam.set_editor_property("use_pawn_control_rotation", False)
    loc = pos + unreal.Vector(205 * math.cos(az), 205 * math.sin(az), 62)
    aim = pos + unreal.Vector(0, 0, 66)
    cam.set_field_of_view(19)
    cam.set_world_location_and_rotation(
        loc, unreal.MathLibrary.find_look_at_rotation(loc, aim), False, True
    )
    if index == 0:
        pp = cam.get_editor_property("post_process_settings")
        for key, val in (
            ("depth_of_field_focal_distance", 189),
            ("depth_of_field_fstop", 4),
            ("depth_of_field_sensor_width", 36),
        ):
            pp.set_editor_property("override_" + key, True)
            pp.set_editor_property(key, val)
        cam.set_editor_property("post_process_settings", pp)
    if moving:
        if elapsed >= 10:
            unreal.log("VESPER_GAZE_DONE")
            unreal.unregister_slate_post_tick_callback(handle)
        return
    # Give temporal antialiasing time to settle on the same pose in every frame.
    if index == 0 and elapsed > 1.5:
        pawn.mesh.set_editor_property("global_anim_rate_scale", 0.0)
    if elapsed < 4 or pawn.mesh.get_morph_target(runtime["blink"].target) > 0.025:
        return
    gaze = runtime["gaze"]
    pigment = gaze.material.get_vector_parameter_value("IrisDirection")
    samples.append(
        dict(
            view=name,
            target=(gaze.target == keeper),
            degrees=[math.degrees(x) for x in gaze.angles],
            pigment=[pigment.r, pigment.g],
        )
    )
    unreal.log("VESPER_GAZE_FRAME " + name + " " + str(samples[-1]))
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    index += 1
    started = time.monotonic()
    if index == len(cases):
        saved = Path(
            unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
        )
        (saved / "WayfarerGaze.json").write_text(json.dumps(samples))
        pawn.mesh.set_editor_property("global_anim_rate_scale", 1.0)
        unreal.log("VESPER_GAZE_CROSSING")


handle = unreal.register_slate_post_tick_callback(tick)
