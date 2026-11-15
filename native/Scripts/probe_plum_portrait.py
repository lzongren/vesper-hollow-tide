"""Photograph the possessed pawn in the existing light of the procession road."""

from pathlib import Path
from math import cos, radians, sin
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
views = [
    ("courtyard", 215, -23, 258, 72, 20),
    ("eaves", 192, -15, 265, 72, 20),
    ("close", 222, -10, 205, 66, 19),
]
if unreal.SystemLibrary.parse_param(
    unreal.SystemLibrary.get_command_line(), "JadeSwallowPortrait"
):
    views = [
        ("front", 222, -10, 205, 66, 19),
        ("swallow", 202, 22, 220, 67, 20),
        ("profile", 222, -39, 224, 59, 25),
        ("reverse", 222, 151, 285, 53, 33),
        ("dress", 222, 18, 478, 2, 39),
    ]
if unreal.SystemLibrary.parse_param(
    unreal.SystemLibrary.get_command_line(), "WayfarerSilhouette"
):
    views = [
        ("front", 222, 18, 478, 2, 39),
        ("side", 222, 83, 478, 2, 39),
        ("back", 222, 161, 478, 2, 39),
    ]
if unreal.SystemLibrary.parse_param(
    unreal.SystemLibrary.get_command_line(), "SpectrePortrait"
):
    views += [
        ("crown", 222, 12, 272, 82, 25),
        ("silhouette", 222, 15, 540, 16, 42),
    ]
idx = 0
start = None


def tick(dt):
    global idx, start
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    if start is None:
        pawn.set_actor_location(unreal.Vector(1670, 30, 110), False, True)
        unreal.log("PLUM_PORTRAIT_MESH " + pawn.mesh.skeletal_mesh_asset.get_name())
        start = time.monotonic()
    name, yaw, turn, distance, aim_height, fov = views[idx]
    pawn.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
    step.pc.set_control_rotation(unreal.Rotator(yaw=yaw))
    pos = pawn.get_actor_location()
    az = radians(yaw + turn)
    cam = pawn.get_component_by_class(unreal.CameraComponent)
    cam.set_absolute(True, True, False)
    cam.set_editor_property("use_pawn_control_rotation", False)
    loc = pos + unreal.Vector(distance * cos(az), distance * sin(az), aim_height - 4)
    aim = pos + unreal.Vector(0, 0, aim_height)
    cam.set_field_of_view(fov)
    cam.set_world_location_and_rotation(
        loc, unreal.MathLibrary.find_look_at_rotation(loc, aim), False, True
    )
    pp = cam.get_editor_property("post_process_settings")
    for key, val in (
        ("depth_of_field_focal_distance", distance - 16),
        ("depth_of_field_fstop", 4.0),
        ("depth_of_field_sensor_width", 36.0),
    ):
        pp.set_editor_property("override_" + key, True)
        pp.set_editor_property(key, val)
    cam.set_editor_property("post_process_settings", pp)
    if (
        time.monotonic() - start < 4
        or pawn.mesh.get_morph_target(runtime["blink"].target) > 0.04
    ):
        return
    unreal.log("PLUM_PORTRAIT " + name)
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    idx += 1
    start = time.monotonic()
    if idx == len(views):
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
