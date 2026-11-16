"""Photograph the belfry approach from the road, plinth and court."""

from pathlib import Path
import json
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
views = [
    ("entry", (2070, -125, 168), (3060, 0, 148), 65),
    ("carving", (2610, -105, 180), (3015, -337, 151), 46),
    ("figure", (2490, -44, 156), (3030, -337, 155), 58),
    ("court", (3890, 96, 155), (2915, 15, 135), 62),
]
start = None
index = 0


def verify_passage(pawn):
    """Check the two solid pedestals and the playable centre at knee height."""
    hits = {}
    for side, y in (("north", -337), ("centre", 0), ("south", 337)):
        hit = unreal.SystemLibrary.line_trace_single(
            pawn,
            unreal.Vector(2810, y, 55),
            unreal.Vector(3250, y, 55),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True,
            [pawn],
            unreal.DrawDebugTrace.NONE,
            True,
        )
        if hit:
            contact = hit.to_tuple()
            actor = contact[9]
            hits[side] = actor.get_actor_label() if actor else None
        else:
            hits[side] = None
    unreal.log("VESPER_LION_PASSAGE " + json.dumps(hits))
    if hits["centre"] or any(
        not str(hits[k]).startswith("Bell gate ") for k in ("north", "south")
    ):
        raise RuntimeError("Unexpected guardian collision " + str(hits))


def tick(_dt):
    global start, index
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    if start is None:
        if "-CheckGate" in unreal.SystemLibrary.get_command_line():
            try:
                verify_passage(pawn)
            except Exception as error:
                unreal.log_error("VESPER_LION_TRACE_FAILED " + str(error))
        pawn.set_actor_location(unreal.Vector(2365, 78, 112), False, True)
        pawn.set_actor_rotation(unreal.Rotator(yaw=1), False)
        step.pc.set_control_rotation(unreal.Rotator(yaw=1))
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
    unreal.log("VESPER_LION_VIEW " + name)
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    index += 1
    start = time.monotonic()
    if index == len(views):
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
