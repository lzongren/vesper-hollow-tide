"""Capture the same tree lines from the bell court, mountain road and final shrine."""

from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
views = [
    ("gate", (2490, -44, 156), (3030, -337, 155), 58),
    ("road", (1335, -635, 149), (1770, -315, 141), 59),
    ("ridge", (18500, -680, 215), (21000, -19500, 3250), 64),
]
isolate = "-IsolateCanopy" in unreal.SystemLibrary.get_command_line()
if isolate:
    views.append(("without-groves", *views[0][1:]))
start = None
index = 0
hidden_grove = None


def tick(_dt):
    global start, index, hidden_grove
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    if start is None:
        pawn.set_actor_location(unreal.Vector(1747, -245, 112), False, True)
        pawn.set_actor_rotation(unreal.Rotator(yaw=190), False)
        step.pc.set_control_rotation(unreal.Rotator(yaw=190))
        start = time.monotonic()
    if index == len(views):
        if time.monotonic() - start > 1:
            if hidden_grove:
                hidden_grove.set_actor_hidden_in_game(False)
            unreal.unregister_slate_post_tick_callback(handle)
        return
    name, loc, aim, fov = views[index]
    if name == "without-groves" and hidden_grove is None:
        hidden_grove = next(
            a
            for a in unreal.GameplayStatics.get_all_actors_of_class(
                pawn, unreal.StaticMeshActor
            )
            if a.get_actor_label() == "Xingping RiverGroves"
        )
        hidden_grove.set_actor_hidden_in_game(True)
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
    unreal.log("VESPER_CANOPY_VIEW " + name)
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    index += 1
    start = time.monotonic()


handle = unreal.register_slate_post_tick_callback(tick)
