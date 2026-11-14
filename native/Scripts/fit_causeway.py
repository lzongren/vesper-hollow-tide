"""Face the exposed road and court foundations with dry-laid stone and fit the three stairs."""

import itertools
import json
import math
import runpy
from pathlib import Path

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
layout = runpy.run_path(str(project / "Scripts" / "road_outline.py"))
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
level = "/Game/Vesper/Maps/MountainPilgrimage"
folder = "/Game/Vesper/RouteArt/Ashlar"
if not levels.load_level(level):
    raise RuntimeError("Cannot load the pilgrimage map")
if not lib.does_directory_exist(folder):
    imp = unreal.AssetImportTask()
    imp.filename = str(project / "Art" / "CausewayAshlar.glb")
    imp.destination_path = folder
    imp.automated = imp.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([imp])
meshes = {}
for path in lib.list_assets(folder):
    if str(lib.find_asset_data(path).asset_class_path.asset_name) == "StaticMesh":
        mesh = lib.load_asset(path)
        meshes[mesh.get_name()] = mesh
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", settings)
        body = mesh.get_editor_property("body_setup")
        body.set_editor_property(
            "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
        )
        if not lib.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError("Failed to save " + path)
bays = [meshes["AshlarBay" + str(i)] for i in range(1, 4)]
tread = meshes["DescentTread"]


def place(mesh, x, y, z, yaw, long_scale, label, collision):
    ext = mesh.get_bounds().box_extent
    along_x = ext.x > ext.y
    rot = yaw if along_x else yaw - 90
    actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator(0, 0, rot)
    )
    actor.static_mesh_component.set_static_mesh(mesh)
    scale = (long_scale, 1, 1) if along_x else (1, long_scale, 1)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.set_actor_label(label)
    actor.set_actor_enable_collision(collision)
    return actor


stairs = []
for a in actors.get_all_level_actors():
    label = a.get_actor_label()
    if label.startswith(("Retaining bay", "Dressed descent", "Descent walking slope")):
        actors.destroy_actor(a)
    elif label == "Valley floor":
        valley = a
    elif label.startswith("Valley stair"):
        stairs.append(a)
if len(stairs) != 96:
    raise RuntimeError("Expected the three valley descents")
for a in stairs:
    pos = a.get_actor_location()
    x, y, z = pos.x, pos.y, pos.z
    a.set_actor_enable_collision(False)
    # Keep the dressed surface visible above its original tread.
    place(tread, x, y, z + 16, 0, 1, "Dressed descent", False)

# The commandlet does not run a physics scene. Read the same triangulated mesh
# used for complex collision, with the placed valley actor's world origin.
glb_reader = runpy.run_path(str(project / "Scripts" / "bind_pilgrim.py"))["Glb"]
terrain = glb_reader(project / "Art" / "MountainValley.glb")
primitive = terrain.doc["meshes"][0]["primitives"][0]
vertices = terrain.values(primitive["attributes"]["POSITION"])
triangles = terrain.values(primitive["indices"])
origin = valley.get_actor_location()


def floor_height(wx, wy):
    x, z = (wx - origin.x) / 100, (wy - origin.y) / 100
    for i in range(0, len(triangles), 3):
        a, b, c = (vertices[triangles[i + j][0]] for j in range(3))
        if not (
            min(a[0], b[0], c[0]) <= x <= max(a[0], b[0], c[0])
            and min(a[2], b[2], c[2]) <= z <= max(a[2], b[2], c[2])
        ):
            continue
        bx, bz = b[0] - a[0], b[2] - a[2]
        cx, cz = c[0] - a[0], c[2] - a[2]
        det = bx * cz - bz * cx
        u = ((x - a[0]) * cz - (z - a[2]) * cx) / det
        v = (bx * (z - a[2]) - bz * (x - a[0])) / det
        if min(u, v, 1 - u - v) >= -1e-7:
            return origin.z + 100 * (a[1] + u * (b[1] - a[1]) + v * (c[1] - a[1]))
    raise RuntimeError(f"Outside the authored valley mesh at {wx}, {wy}")


extra_treads = []
for sx, sy in layout["POINTS"][1::2]:
    added = 0
    for k in range(32, 64):
        y = sy - 1400 - 32 * k
        top = 1 - 15 * k
        if top < floor_height(sx, y) - 8:
            break
        place(tread, sx, y, top, 0, 1, "Dressed descent apron", False)
        added += 1
    else:
        raise RuntimeError("Stair did not meet the terrain")
    extra_treads.append(added)

# A continuous walking surface avoids capsule catches on the vertical lips of
# the individually chipped visual treads in both directions.
cube = lib.load_asset("/Engine/BasicShapes/Cube.Cube")
for (sx, sy), extra in zip(layout["POINTS"][1::2], extra_treads):
    steps = 32 + extra
    run = 32 * steps
    rise = 15 * steps
    angle = math.atan2(rise, run)
    depth = 38
    # Midplane of the slanted box is half a thickness inward from the surface.
    y = sy - 1400 + 16 - run / 2 + math.sin(angle) * depth / 2
    z = 8.5 - rise / 2 - math.cos(angle) * depth / 2
    actor = actors.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(sx, y, z),
        unreal.Rotator(0, math.degrees(angle), 90),
    )
    actor.static_mesh_component.set_static_mesh(cube)
    actor.set_actor_scale3d(
        unreal.Vector(math.hypot(run, rise) / 100, 2.56, depth / 100)
    )
    actor.set_actor_label("Descent walking slope")
    actor.set_actor_hidden_in_game(True)

count = 0
length_sum = 0
for edge, (a, b) in enumerate(layout["boundary"](layout["decks"]())):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1:
        continue
    nx, ny = dy / length, -dx / length
    yaw = math.degrees(math.atan2(dy, dx))
    # Leave openings opposite the three flights, including room for both stone curbs.
    cuts = [0, length]
    for sx, sy in layout["POINTS"][1::2]:
        if abs(dy) < 0.01 and abs(a[1] - (sy - 1400)) < 0.01:
            center = (sx - a[0]) * dx / length
            cuts.extend(
                [max(0, min(length, center - 151)), max(0, min(length, center + 151))]
            )
    cuts = sorted(set(cuts))
    for lo, hi in itertools.pairwise(cuts):
        mid = (lo + hi) * 0.5
        cx, cy = a[0] + dx / length * mid, a[1] + dy / length * mid
        if any(
            abs(cy - (sy - 1400)) < 0.01 and abs(cx - sx) < 151
            for sx, sy in layout["POINTS"][1::2]
        ):
            continue
        n = max(1, round((hi - lo) / 640))
        for k in range(n):
            distance = lo + (k + 0.5) * (hi - lo) / n
            place(
                bays[(edge + k) % 3],
                a[0] + dx / length * distance + nx * 5,
                a[1] + dy / length * distance + ny * 5,
                0,
                yaw,
                (hi - lo) / n / 640,
                "Retaining bay",
                True,
            )
            count += 1
        length_sum += hi - lo
if not levels.save_current_level():
    raise RuntimeError("Failed to save the fitted causeway")
report = {
    "bays": count,
    "wall_metres": round(length_sum / 100, 2),
    "treads": len(stairs) + sum(extra_treads),
    "apron_treads": extra_treads,
    "mesh_names": sorted(meshes),
}
(project / "Saved" / "Ashlar.json").write_text(json.dumps(report, indent=2))
unreal.log("VESPER_ASHLAR_SAVED " + str(report))
