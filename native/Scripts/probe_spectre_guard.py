"""Photograph the shoulder as a real player-input sword montage plays."""

from pathlib import Path
from math import cos, radians, sin
import runpy
import unreal

game = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = game["step"]
start = None
next_press = 1.1
pressed_at = None
captured = set()


def tick(dt):
    global start, pressed_at, next_press
    pawn = step.pawn
    if not game["live"](pawn):
        return
    now = unreal.GameplayStatics.get_time_seconds(pawn)
    if start is None:
        start = now
        pawn.set_actor_location(unreal.Vector(1670, 30, 110), False, True)
        pawn.set_actor_rotation(unreal.Rotator(yaw=222), False)
        step.pc.set_control_rotation(unreal.Rotator(yaw=222))
        unreal.log("SPECTRE_GUARD_MESH " + pawn.mesh.skeletal_mesh_asset.get_name())
    age = now - start
    pos = pawn.get_actor_location()
    cam = pawn.get_component_by_class(unreal.CameraComponent)
    cam.set_absolute(True, True, False)
    cam.set_editor_property("use_pawn_control_rotation", False)
    a = radians(222 + 32)
    eye = pos + unreal.Vector(294 * cos(a), 294 * sin(a), 57)
    aim = pos + unreal.Vector(0, 0, 54)
    cam.set_world_location_and_rotation(
        eye, unreal.MathLibrary.find_look_at_rotation(eye, aim), False, True
    )
    cam.set_field_of_view(31)

    def key(command):
        unreal.SystemLibrary.execute_console_command(pawn, command, step.pc)

    if pressed_at is not None and age - pressed_at > 0.10:
        key("Input.-key LeftMouseButton")
        pressed_at = None
    if age >= next_press:
        key("Input.+key LeftMouseButton 1")
        pressed_at = age
        next_press += 1.55
    anim = pawn.mesh.get_anim_instance()
    montage = anim.get_current_active_montage() if anim else None
    if montage:
        at = anim.montage_get_position(montage)
        phase = "lift" if 0.09 < at < 0.21 else "cut" if 0.28 < at < 0.43 else None
        if phase and phase not in captured and age > 3:
            loc = pawn.mesh.get_socket_location("upperarm_r") - pos
            unreal.log(f"SPECTRE_GUARD {phase} {montage.get_name()} {at:.3f} {loc}")
            key("Shot")
            captured.add(phase)
    if age > 18 or len(captured) == 2:
        if pressed_at is not None:
            key("Input.-key LeftMouseButton")
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.log("SPECTRE_GUARD_DONE " + str(sorted(captured)))


handle = unreal.register_slate_post_tick_callback(tick)
