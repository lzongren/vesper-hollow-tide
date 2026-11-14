"""Capture the playable swordswoman at five repeatable camera positions."""

from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
shots = [(4, "rear"), (8, "front"), (12, "profile"), (19, "walk"), (25, "portrait")]
start = camera = None


def tick(_dt):
    global start, camera
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    if start is None:
        pawn.set_actor_location(unreal.Vector(1350, 50, 110), False, True)
        pawn.set_actor_rotation(unreal.Rotator(yaw=0), False)
        step.pc.set_control_rotation(unreal.Rotator(pitch=-6, yaw=0))
        camera = pawn.get_component_by_class(unreal.CameraComponent)
        camera.set_absolute(True, True, False)
        camera.set_editor_property("use_pawn_control_rotation", False)
        start = time.monotonic()
        unreal.log("TAILOR_SKIN " + pawn.mesh.skeletal_mesh_asset.get_name())
    elapsed = time.monotonic() - start
    pos = pawn.get_actor_location()
    aim_height = 12
    if elapsed < 5.5:
        offset, lens = (-395, -135, 63), 54
    elif elapsed < 9.5:
        offset, lens = (200, -70, 83), 36
        aim_height = 67
    elif elapsed < 13.5:
        offset, lens = (255, 245, 68), 52
    elif elapsed < 19.5:
        offset, lens = (-399, -117, 54), 55
        pawn.add_movement_input(unreal.Vector(1, 0, 0), 0.67)
    else:
        # Face into the open courtyard light for a second view of the complexion.
        pawn.set_actor_rotation(unreal.Rotator(yaw=198), False)
        step.pc.set_control_rotation(unreal.Rotator(yaw=198))
        offset, lens = (-175, -67, 74), 29
        aim_height = 65
    aim = pos + unreal.Vector(0, 0, aim_height)
    loc = pos + unreal.Vector(*offset)
    camera.set_world_location_and_rotation(
        loc, unreal.MathLibrary.find_look_at_rotation(loc, aim), False, True
    )
    camera.set_field_of_view(lens)
    if elapsed >= shots[0][0]:
        unreal.log("TAILOR_SHOT " + shots.pop(0)[1])
        unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    if not shots:
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
