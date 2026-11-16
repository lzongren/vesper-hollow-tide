"""Walk the bridge through the ordinary possession, movement and camera path."""

import json
import math
from pathlib import Path
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
from_court = unreal.SystemLibrary.parse_param(
    unreal.SystemLibrary.get_command_line(), "GardenWalkFromCourt"
)
origin = (12830, 2850) if from_court else (14140, 921)
route = (
    [(12950, 2880), (12950, 3676), (14140, 3676), (14140, 921)]
    if from_court
    else [(14140, 3640)]
)
start = None
index = 0
last = -1
samples = []
shots = {}


def finish(pawn, status):
    data = dict(
        outcome=status,
        from_court=from_court,
        mesh=pawn.mesh.skeletal_mesh_asset.get_name(),
        samples=samples,
        shot_clock=shots,
    )
    saved = Path(
        unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    )
    (
        saved / ("LotusCourtWalk.json" if from_court else "LotusCrossing.json")
    ).write_text(json.dumps(data))
    unreal.log("VESPER_LOTUS_CROSSING " + status)
    unreal.unregister_slate_post_tick_callback(handle)


def tick(dt):
    global start, index, last
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    now = unreal.GameplayStatics.get_time_seconds(pawn)
    if start is None:
        pawn.set_actor_location_and_rotation(
            unreal.Vector(*origin, 118), unreal.Rotator(yaw=90), False, True
        )
        start = now
    age = now - start
    pos = pawn.get_actor_location()
    if age - last >= 0.12:
        hit = unreal.SystemLibrary.line_trace_single(
            pawn,
            pos,
            pos - unreal.Vector(0, 0, 270),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True,
            [pawn],
            unreal.DrawDebugTrace.NONE,
            True,
        )
        name = hit.to_tuple()[9].get_actor_label() if hit else None
        samples.append(
            [round(age, 2), round(pos.x, 1), round(pos.y, 1), round(pos.z, 1), name]
        )
        last = age
    if index == len(route) - 1:
        travel = (3676 - pos.y) if from_court else (pos.y - 921)
        for distance, tag in ((410, "ascent"), (1319, "crown"), (2099, "descent")):
            if travel >= distance and tag not in shots:
                shots[tag] = time.perf_counter()
                unreal.log("VESPER_LOTUS_STEP " + tag)
                unreal.SystemLibrary.execute_console_command(
                    pawn, "Shot SHOWUI", step.pc
                )
    x, y = route[index]
    dx, dy = x - pos.x, y - pos.y
    dist = math.hypot(dx, dy)
    if dist < 28:
        index += 1
        if index == len(route):
            return finish(pawn, "crossed")
        return
    if age > 38 or pos.z < -250:
        return finish(pawn, "stalled")
    yaw = math.degrees(math.atan2(dy, dx))
    step.pc.set_control_rotation(unreal.Rotator(pitch=-11, yaw=yaw))
    if age > 5:
        pawn.add_movement_input(unreal.Vector(dx / dist, dy / dist, 0), 1)


handle = unreal.register_slate_post_tick_callback(tick)
