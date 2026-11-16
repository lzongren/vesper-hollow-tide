"""Photograph a road lamp from two fixed world-space cameras beside the possessed player."""

from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
views = [
    ("road", (1335, -635, 149), (1770, -315, 141), 59),
    ("casting", (1510, -544, 180), (1764, -391, 159), 46),
]
start = None
index = 0


def tick(_dt):
    global start, index
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    if start is None:
        pawn.set_actor_location(unreal.Vector(1747, -245, 112), False, True)
        pawn.set_actor_rotation(unreal.Rotator(yaw=190), False)
        step.pc.set_control_rotation(unreal.Rotator(yaw=190))
        start = time.monotonic()
    name, loc, aim, fov = views[index]
    cam = pawn.get_component_by_class(unreal.CameraComponent)
    cam.set_absolute(True, True, False)
    cam.set_editor_property("use_pawn_control_rotation", False)
    loc = unreal.Vector(*loc)
    cam.set_world_location_and_rotation(
        loc,
        unreal.MathLibrary.find_look_at_rotation(loc, unreal.Vector(*aim)),
        False,
        True,
    )
    cam.set_field_of_view(fov)
    if time.monotonic() - start < 5:
        return
    unreal.log("VESPER_LAMP_VIEW " + name)
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    index += 1
    start = time.monotonic()
    if index == len(views):
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
