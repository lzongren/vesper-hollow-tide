"""Replace the valley's placeholder tree meshes and seat their roots on the imported terrain."""

import json
import math
import runpy
from pathlib import Path

import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
lib = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level("/Game/Vesper/Maps/MountainPilgrimage"):
    raise RuntimeError("Missing mountain pilgrimage")
folder = "/Game/Vesper/RouteArt/MountainPines"
if not lib.does_directory_exist(folder):
    imp = unreal.AssetImportTask()
    imp.filename = str(project / "Art" / "MountainPines.glb")
    imp.destination_path = folder
    imp.automated = imp.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([imp])
meshes = {}
for path in lib.list_assets(folder):
    if str(lib.find_asset_data(path).asset_class_path.asset_name) == "StaticMesh":
        mesh = lib.load_asset(path)
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", settings)
        if not lib.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError("Cannot save " + path)
        meshes[mesh.get_name()] = mesh
if set(meshes) != {"WindPine", "RidgePine"}:
    raise RuntimeError("Expected two pine shapes, found " + str(meshes))
all_actors = actors.get_all_level_actors()
valley = next(a for a in all_actors if a.get_actor_label() == "Valley floor")
origin = valley.get_actor_location()
read = runpy.run_path(str(project / "Scripts" / "bind_pilgrim.py"))["Glb"]
terrain = read(project / "Art" / "MountainValley.glb")
prim = terrain.doc["meshes"][0]["primitives"][0]
verts = terrain.values(prim["attributes"]["POSITION"])
side = math.isqrt(len(verts))
step = verts[1][0] - verts[0][0]
if side * side != len(verts) or step <= 0:
    raise RuntimeError("Unexpected valley grid")


def ground(x, y):
    gx = ((x - origin.x) / 100 - verts[0][0]) / step
    gz = ((y - origin.y) / 100 - verts[0][2]) / step
    i, j = math.floor(gx), math.floor(gz)
    if not (0 <= i < side - 1 and 0 <= j < side - 1):
        raise RuntimeError("Tree outside the authored valley")
    u, v = gx - i, gz - j
    a = verts[j * side + i][1]
    b = verts[j * side + i + 1][1]
    c = verts[(j + 1) * side + i][1]
    d = verts[(j + 1) * side + i + 1][1]
    return origin.z + 100 * (
        a * (1 - max(u, v)) + b * max(0, u - v) + c * max(0, v - u) + d * min(u, v)
    )


trees = sorted(
    (a for a in all_actors if a.get_actor_label().startswith("Mountain pine")),
    key=lambda a: a.get_actor_label(),
)
if len(trees) != 120:
    raise RuntimeError("Expected 120 mountain pines")
for i, a in enumerate(trees):
    p = a.get_actor_location()
    # Keep a canopy and camera corridor along each stair, including its landing.
    # Snap to the outside of the closest flight only when the trunk is too close.
    x, y = p.x, p.y
    for sx, sy in [(4200, 0), (11500, 1600), (19400, -800)]:
        cy = min(sy - 1050, max(sy - 2800, y))
        dx, dy = x - sx, y - cy
        dist = math.hypot(dx, dy)
        if dist < 865:
            if dist < 0.01:
                dx, dy, dist = 1, 0, 1
            x = sx + 865 * dx / dist
            y = cy + 865 * dy / dist
    scale = 0.77 + 0.62 * (0.5 + 0.5 * math.sin(x * 0.371 + y * 0.739))
    name = ["WindPine", "RidgePine"][i % 2]
    a.static_mesh_component.set_static_mesh(meshes[name])
    a.set_actor_location(unreal.Vector(x, y, ground(x, y) - 6), False, True)
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    a.set_actor_enable_collision(False)
if not levels.save_current_level():
    raise RuntimeError("Failed to save pine grove")
report = {
    "trees": len(trees),
    "variants": {
        k: {
            "instances": len(trees) // 2,
            "slots": len(m.get_editor_property("static_materials")),
        }
        for k, m in meshes.items()
    },
}
(project / "Saved" / "Pines.json").write_text(json.dumps(report, indent=2))
unreal.log("VESPER_PINES_SAVED " + str(report))
