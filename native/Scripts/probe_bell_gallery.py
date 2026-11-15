"""Repeatable approach and fighting-distance photographs of the first court."""

from pathlib import Path
import json
import runpy
import time

import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
# Camera, aim, field of view, player, keeper. Units are centimetres.
views = [
    ("gate", (1730, -125, 172), (3530, 35, 189), 60, (2145, 0), (3850, 0)),
    ("duel", (3320, -186, 154), (3750, 28, 118), 57, (3600, -22), (3890, 30)),
    ("screen", (3790, 267, 163), (3700, -234, 151), 62, (3610, -24), (3850, 42)),
    ("exit", (4240, -166, 148), (4920, 40, 154), 63, (4560, 12), (4850, 55)),
]
index = 0
entered = None


def survey(pawn, keeper):
    found = unreal.GameplayStatics.get_all_actors_with_tag(pawn, "VesperBellRain")
    if not found:
        return

    def trace(start, end):
        hit = unreal.SystemLibrary.line_trace_single(
            pawn,
            unreal.Vector(*start),
            unreal.Vector(*end),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True,
            [pawn, keeper],
            unreal.DrawDebugTrace.NONE,
            True,
        )
        if not hit:
            return None
        info = hit.to_tuple()
        return [info[9].get_actor_label(), round(info[4].z, 1)]

    checks = {
        "ridge_from_above": trace((3730, 0, 1080), (3730, 0, 130)),
        "entrance_post": trace((2900, 545, 140), (3230, 545, 140)),
        "carved_screen": trace((4180, 624, 218), (4650, 624, 218)),
        "centre_lane": [trace((3000, y, 110), (4440, y, 110)) for y in (-170, 0, 170)],
    }
    controls = {
        a.get_actor_label(): a.light_component.intensity
        for a in found
        if isinstance(a, unreal.Light)
    }
    saved = Path(
        unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    )
    (saved / "BellGallerySurvey.json").write_text(
        json.dumps(dict(actors=len(found), lights=controls, collision=checks))
    )
    unreal.log("VESPER_BELL_GALLERY_SURVEY " + str(checks))
    views.append(
        ("carving", (4170, 958, 226), (4487, 622, 235), 68, (3950, 150), (3750, 20))
    )
    views.append(
        ("roofline", (1520, -1035, 335), (3730, 35, 323), 65, (2470, 10), (3760, 25))
    )


def tick(dt):
    global index, entered
    pawn, keeper = step.pawn, runtime["boss"].actor
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
    unreal.log("VESPER_BELL_GALLERY_VIEW " + name)
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    index += 1
    entered = None
    if index == len(views):
        unreal.log("VESPER_BELL_GALLERY_VIEWS_DONE")
        unreal.unregister_slate_post_tick_callback(handle)


handle = unreal.register_slate_post_tick_callback(tick)
