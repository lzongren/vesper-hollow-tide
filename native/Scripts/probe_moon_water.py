"""Photograph the moon court from repeatable combat and waterside viewpoints."""

from pathlib import Path
import json
import runpy
import time

import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
# Camera, aim, field of view, player, keeper. Units are centimetres.
views = [
    (
        "encounter",
        (11025, 1465, 157),
        (11840, 1680, 154),
        59,
        (11325, 1525),
        (11630, 1645),
    ),
    ("shore", (12560, 1960, 167), (14250, 2200, 95), 64, (12100, 1350), (11850, 1440)),
    (
        "bridge",
        (13140, 1250, 145),
        (14520, 2210, 130),
        59,
        (12100, 1350),
        (11850, 1440),
    ),
    (
        "terrace",
        (12600, 2870, 245),
        (14430, 1970, 50),
        68,
        (12100, 1350),
        (11850, 1440),
    ),
]
views.append(
    ("lotus", (13025, 3055, 68), (13405, 3270, -54), 43, (12100, 1350), (11850, 1440))
)
index = 0
entered = None


def survey(pawn, keeper):
    rows = {}
    for x in (12730, 13100, 14100, 14900, 15600):
        for y in (1000, 1800, 2600, 3400):
            hit = unreal.SystemLibrary.line_trace_single(
                pawn,
                unreal.Vector(x, y, 3400),
                unreal.Vector(x, y, -2800),
                unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                True,
                [pawn, keeper],
                unreal.DrawDebugTrace.NONE,
                True,
            )
            if hit:
                info = hit.to_tuple()
                rows[f"{x},{y}"] = [info[9].get_actor_label(), round(info[4].z, 1)]
    saved = Path(
        unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    )
    (saved / "MoonWaterSurvey.json").write_text(json.dumps(rows))


def tick(dt):
    global index, entered
    pawn, keeper = step.pawn, runtime["heron"].actor
    if not runtime["live"](pawn) or not runtime["live"](keeper):
        return
    name, location, aim, fov, player_xy, keeper_xy = views[index]
    if entered is None:
        if index == 0:
            survey(pawn, keeper)
        for actor, point, yaw, clip, stamp in (
            (pawn, player_xy, 12, "MM_Attack_01", 0.24),
            (keeper, keeper_xy, 195, "MM_ChargedAttack", 0.41),
        ):
            actor.character_movement.disable_movement()
            actor.set_actor_location_and_rotation(
                unreal.Vector(*point, 103), unreal.Rotator(yaw=yaw), False, True
            )
            pose = unreal.load_asset(
                "/Game/Characters/Mannequins/Anims/Unarmed/Attack/" + clip
            )
            actor.mesh.play_animation(pose, False)
            actor.mesh.set_position(stamp, False)
            actor.mesh.set_play_rate(0)
        entered = time.monotonic()
    cam = pawn.get_component_by_class(unreal.CameraComponent)
    cam.set_absolute(True, True, False)
    cam.set_editor_property("use_pawn_control_rotation", False)
    pos = unreal.Vector(*location)
    cam.set_world_location_and_rotation(
        pos,
        unreal.MathLibrary.find_look_at_rotation(pos, unreal.Vector(*aim)),
        False,
        True,
    )
    cam.set_field_of_view(fov)
    if time.monotonic() - entered < 3.5:
        return
    unreal.log("VESPER_MOON_WATER_VIEW " + name)
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    index += 1
    entered = None
    if index == len(views):
        unreal.log("VESPER_MOON_WATER_DONE")
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
