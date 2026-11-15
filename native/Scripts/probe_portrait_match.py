"""Capture the live player from a camera aligned to the animated head axes."""

import math
from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
from wayfarer_gaze import head_axes

step = runtime["step"]
views = [("closed", 0, 1), ("open", 0, 0), ("turn", 34, 0)]
index = 0
blink_driver = runtime["blink"]
intervals = blink_driver.intervals
# The ordinary combat tick runs before the photographic probe. Keep it from
# starting another blink while an endpoint is being measured.
blink_driver.intervals = (3600.0,)
start = axes = requested = None


def tick(dt):
    global start, axes, index, requested
    pawn = step.pawn
    if not runtime["live"](pawn) or not runtime["blink"].target:
        return
    if axes is None:
        pawn.set_actor_location_and_rotation(
            unreal.Vector(1670, 30, 110), unreal.Rotator(yaw=222), False, True
        )
        step.pc.set_control_rotation(unreal.Rotator(yaw=222))
        axes = head_axes(pawn)
        unreal.log("PORTRAIT_MATCH_MESH " + pawn.mesh.skeletal_mesh_asset.get_name())
        start = time.monotonic()
    mode, turn, blink = views[index]
    head = pawn.mesh.get_socket_transform("head")
    fwd, right, up = (unreal.MathLibrary.transform_direction(head, x) for x in axes)
    angle = math.radians(turn)
    towards = fwd * math.cos(angle) + right * math.sin(angle)
    center = head.translation + up * 3 + fwd * 8.5
    cam = pawn.get_component_by_class(unreal.CameraComponent)
    cam.set_absolute(True, True, False)
    cam.set_editor_property("use_pawn_control_rotation", False)
    cam.set_world_location_and_rotation(
        center + towards * 200,
        unreal.MathLibrary.make_rot_from_xz(towards * -1, up),
        False,
        True,
    )
    cam.set_field_of_view(14.0)
    blink_driver.pose(blink)
    now = time.monotonic()
    if requested is not None:
        # Shot completes during rendering and can spill into the following tick.
        # Stay on this pose until the PNG for this request is actually present.
        if not (set(captures.glob("ScreenShot*.png")) - requested):
            return
        index += 1
        start = now
        requested = None
        if index == len(views):
            blink_driver.pose(0)
            blink_driver.intervals = intervals
            blink_driver.age = blink_driver.last = 0.0
            blink_driver.index = 0
            unreal.unregister_slate_post_tick_callback(handle)
        return
    if now - start < 5.0:
        return
    unreal.log(
        f"PORTRAIT_MATCH {mode} {pawn.mesh.get_morph_target(runtime['blink'].target):.2f}"
    )
    requested = set(captures.glob("ScreenShot*.png"))
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)


captures = (
    Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
    / "Screenshots/WindowsEditor"
)
handle = unreal.register_slate_post_tick_callback(tick)
