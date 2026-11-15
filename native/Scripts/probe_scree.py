"""Photograph the foot of the shrine crags from fixed court and valley cameras."""

from pathlib import Path
import json
import runpy
import time
import unreal

runtime = runpy.run_path(str(Path(__file__).with_name("belfry_combat.py")))
step = runtime["step"]
views = [
    ("ridge", (18500, -680, 215), (21000, -19500, 3250), 64),
    ("foot", (19150, -3080, -130), (20310, -6410, -70), 58),
    ("garden", (17900, -1790, 90), (21100, -4740, -85), 61),
]
report = (
    Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()))
    / "ShrineTalus.json"
)
if report.exists() and (marker := json.loads(report.read_text()).get("inscription")):
    x, y, z = (100 * n for n in marker)
    views.append(("inscription", (x - 255, y + 665, z + 175), (x, y, z + 167), 47))
    views.append(("trail", (x - 410, y + 990, z + 208), (x + 18, y, z + 150), 54))
start = None
index = 0


def check_collision(pawn):
    def probe(a, b):
        hit = unreal.SystemLibrary.line_trace_single(
            pawn,
            unreal.Vector(*a),
            unreal.Vector(*b),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True,
            [pawn],
            unreal.DrawDebugTrace.NONE,
            True,
        )
        if not hit:
            return None, None
        contact = hit.to_tuple()
        return contact[9], contact[10]

    # Test the actual saved level through the normal game collision scene.
    config = json.loads(report.read_text())
    x, y, z = (100 * n for n in config["inscription"])
    marker, _ = probe((x - 160, y + 480, z + 165), (x + 125, y - 390, z + 165))
    bank_hits = 0
    for gx in range(18000, 21701, 300):
        for gy in range(-8150, -3649, 250):
            actor, component = probe((gx, gy, 1200), (gx, gy, -1400))
            if (
                actor
                and actor.get_actor_label() == "Cinder shrine scree"
                and component == actor.static_mesh_component
            ):
                bank_hits += 1
    owners = unreal.GameplayStatics.get_all_actors_of_class(
        pawn, unreal.StaticMeshActor
    )
    owner = next(a for a in owners if a.get_actor_label() == "Cinder shrine scree")
    counts = {
        c.static_mesh.get_name(): c.get_instance_count()
        for c in owner.get_components_by_class(
            unreal.HierarchicalInstancedStaticMeshComponent
        )
    }
    result = {
        "bank_hits": bank_hits,
        "marker": marker.get_actor_label() if marker else None,
        "instances": counts,
    }
    unreal.log("VESPER_SCREE_SURVEY " + json.dumps(result))
    if (
        counts != config["instances"]
        or bank_hits == 0
        or result["marker"] != "Pine ravine inscription"
    ):
        unreal.log_error("VESPER_SCREE_SURVEY_FAILED")


def tick(_dt):
    global start, index
    pawn = step.pawn
    if not runtime["live"](pawn):
        return
    if start is None:
        if len(views) > 3:
            check_collision(pawn)
        pawn.set_actor_location(unreal.Vector(1747, -245, 112), False, True)
        pawn.set_actor_rotation(unreal.Rotator(yaw=190), False)
        step.pc.set_control_rotation(unreal.Rotator(yaw=190))
        start = time.monotonic()
    name, loc, aim, fov = views[index]
    if name == "trail" and time.monotonic() - start < 1.1:
        target = unreal.Vector(x - 155, y + 445, z + 132)
        pawn.set_actor_location(target, False, True)
        pawn.set_actor_rotation(unreal.Rotator(yaw=-73), False)
        step.pc.set_control_rotation(unreal.Rotator(yaw=-73))
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
    unreal.log("VESPER_SCREE_VIEW " + name)
    unreal.SystemLibrary.execute_console_command(pawn, "Shot", step.pc)
    index += 1
    if index == len(views):
        unreal.unregister_slate_post_tick_callback(handle)
    start = time.monotonic()


handle = unreal.register_slate_post_tick_callback(tick)
