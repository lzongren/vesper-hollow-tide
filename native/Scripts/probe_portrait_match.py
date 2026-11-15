"""Capture the live player from a camera aligned to the animated head axes."""

import math
from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
from wayfarer_gaze import head_axes  # noqa: E402 - combat installs the game script path

step = runtime["step"]
views = [
    ("open", 0, 0),
    ("closed", 0, 1),
    ("turn", 38, 0),
    ("profile", 88, 0),
    ("jaw", 10, 0),
]
shrine = "-ShrinePortrait" in unreal.SystemLibrary.get_command_line()
if shrine:
    views = [("open", 0, 0), ("turn", 38, 0), ("profile", 88, 0), ("behind", 116, 0)]
jaw = None
recording = "-DigitalTurntable" in unreal.SystemLibrary.get_command_line()
turntable = recording or "-PortraitOrbit" in unreal.SystemLibrary.get_command_line()
orbit_start = None
index = 0
blink_driver = runtime["blink"]
runtime["acting"].enabled = False
intervals = blink_driver.intervals
# The ordinary combat tick runs before the photographic probe. Keep it from
# starting another blink while an endpoint is being measured.
blink_driver.intervals = (3600.0,)
start = axes = requested = None


def tick(dt):
    global start, axes, index, requested, jaw, views, turntable, orbit_start
    pawn = step.pawn
    if not runtime["live"](pawn) or not runtime["blink"].target:
        return
    if axes is None:
        location = (
            unreal.Vector(17600, -800, 110) if shrine else unreal.Vector(1670, 30, 110)
        )
        rotation = unreal.Rotator(yaw=142 if shrine else 222)
        pawn.set_actor_location_and_rotation(location, rotation, False, True)
        step.pc.set_control_rotation(rotation)
        axes = head_axes(pawn)
        jaw = next(
            (
                n
                for n in pawn.mesh.skeletal_mesh_asset.get_all_morph_target_names()
                if str(n).lower().endswith("jawopen")
            ),
            None,
        )
        if jaw is None:
            views = [("closed", 0, 1), ("open", 0, 0), ("turn", 34, 0)]
        unreal.log("PORTRAIT_MATCH_MESH " + pawn.mesh.skeletal_mesh_asset.get_name())
        start = time.monotonic()
    mode, turn, blink = views[index]
    jaw_weight = 0.38 if mode == "jaw" else 0
    if turntable:
        now = time.monotonic()
        if orbit_start is None:
            ready = captures.parent.parent / "DigitalHeadRecorder.ready"
            if (
                ready.exists() and abs(time.time() - ready.stat().st_mtime) < 12
            ) or now - start > (20.0 if recording else 1.5):
                orbit_start = now
                unreal.log("DIGITAL_HEAD_ORBIT_START")
        t = 0 if orbit_start is None else now - orbit_start
        arc = 128 if shrine else 98
        turn = -12 + arc * (0.5 - 0.5 * math.cos(math.tau * min(1, t / 12)))
        blink = max(0, 1 - abs(t - 2.8) / 0.14)
        jaw_weight = 0.20 * math.exp(-(((t - 8.0) / 0.9) ** 2))
        if t >= 12:
            turntable = False
            start = now
            unreal.log("DIGITAL_HEAD_ORBIT_END")
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
    if jaw:
        pawn.mesh.set_morph_target(jaw, jaw_weight)
    if turntable:
        return
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
            if jaw:
                pawn.mesh.set_morph_target(jaw, 0)
            blink_driver.pose(0)
            runtime["acting"].enabled = True
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
