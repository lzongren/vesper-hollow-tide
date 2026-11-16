"""Keep the authored low-poly route meshes on the conventional static-mesh path.

Interchange creates material instances of engine-owned glTF masters. In standalone
game mode those masters can lack the Nanite permutation and render as the checker.
The route uses modest meshes and requires neither engine material edits nor a fallback.
"""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
lib = unreal.EditorAssetLibrary
count = 0
for path in lib.list_assets("/Game/Vesper/RouteArt"):
    data = lib.find_asset_data(path)
    if str(data.asset_class_path.asset_name) != "StaticMesh":
        continue
    mesh = lib.load_asset(path)
    settings = mesh.get_editor_property("nanite_settings")
    settings.set_editor_property("enabled", False)
    mesh.set_editor_property("nanite_settings", settings)
    if not lib.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError("Failed to save route mesh " + path)
    count += 1
if not count:
    raise RuntimeError("No route meshes found")
(project / "Saved" / "RouteMeshes.json").write_text(json.dumps({"conventional_meshes":count}))
unreal.log("VESPER_ROUTE_MESHES_READY")
