"""Frame three sightlines from the possessed player in the live mountain map."""

from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
views = [
    ((850, -120, 106), (-1, 0.33, 0.15), 63, "west"),
    ((8100, 1330, 107), (-0.48, 0.88, 0.14), 69, "north"),
    ((17200, -830, 106), (-0.10, -1, 0.19), 65, "south"),
]
index = 0
changed = None


def tick(_dt):
    global index, changed
    pawn = runtime["step"].pawn
    if not runtime["live"](pawn):
        return
    location, direction, fov, name = views[index]
    if changed is None:
        pos = unreal.Vector(*location)
        pawn.set_actor_location(pos, False, True)
        aim = unreal.Vector(*direction).normal()
        orientation = unreal.MathLibrary.find_look_at_rotation(pos, pos + aim * 400)
        pawn.set_actor_rotation(unreal.Rotator(yaw=orientation.yaw), False)
        camera = pawn.get_component_by_class(unreal.CameraComponent)
        camera.set_absolute(True, True, False)
        camera.set_editor_property("use_pawn_control_rotation", False)
        right = unreal.Vector(-aim.y, aim.x, 0)
        origin = pos - aim * 290 + right * 85 + unreal.Vector(0, 0, 112)
        camera.set_world_location_and_rotation(origin, orientation, False, True)
        camera.set_field_of_view(fov)
        changed = time.monotonic()
    elif time.monotonic() - changed > 4:
        unreal.log("VESPER_PASS_VIEW " + name)
        unreal.SystemLibrary.execute_console_command(pawn, "Shot", runtime["step"].pc)
        changed = None
        index += 1
        if index == len(views):
            unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
