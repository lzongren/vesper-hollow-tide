"""Dress the saved traversal map with world-scale stone and distant mountain spurs."""
import json
from pathlib import Path
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
root = "/Game/Vesper/RouteSurfaces"
level = "/Game/Vesper/Maps/MountainPilgrimage"


def texture(channel):
    name = "Stone_" + channel
    existing = lib.load_asset(root + "/" + name) if lib.does_asset_exist(root + "/" + name) else None
    if existing:
        return existing
    task = unreal.AssetImportTask()
    task.filename = str(project / "SourceAssets" / ("stone-" + channel + ".jpg"))
    task.destination_path = root
    task.destination_name = name
    task.automated = task.save = True
    tools.import_asset_tasks([task])
    tex = next(lib.load_asset(p) for p in task.imported_object_paths if isinstance(lib.load_asset(p), unreal.Texture2D))
    if channel == "normal":
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
    elif channel == "rough":
        tex.set_editor_property("srgb", False)
    lib.save_loaded_asset(tex)
    return tex


def paving_material():
    path = root + "/RoadStone"
    if lib.does_asset_exist(path):
        return lib.load_asset(path)
    tex = {k:texture(k) for k in ("color","normal","rough")}
    mat = tools.create_asset("RoadStone",root,unreal.Material,unreal.MaterialFactoryNew())
    edit = unreal.MaterialEditingLibrary
    def node(cls,x,y):
        return edit.create_material_expression(mat,cls,x,y)
    position = node(unreal.MaterialExpressionWorldPosition,-780,0)
    mask = node(unreal.MaterialExpressionComponentMask,-580,0)
    mask.set_editor_property("R", True)
    mask.set_editor_property("G", True)
    edit.connect_material_expressions(position,"",mask,"Input")
    scale = node(unreal.MaterialExpressionMultiply,-390,0)
    scale.set_editor_property("ConstB", 1.0/220)
    edit.connect_material_expressions(mask,"",scale,"A")
    for i,(key,target) in enumerate([
        ("color",unreal.MaterialProperty.MP_BASE_COLOR),("normal",unreal.MaterialProperty.MP_NORMAL),
        ("rough",unreal.MaterialProperty.MP_ROUGHNESS)]):
        sample = node(unreal.MaterialExpressionTextureSample,-150,i*185)
        sample.set_editor_property("Texture", tex[key])
        if key=="normal":
            sample.set_editor_property("SamplerType", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        elif key=="rough":
            sample.set_editor_property("SamplerType", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        edit.connect_material_expressions(scale,"",sample,"UVs")
        edit.connect_material_property(sample,"R" if key=="rough" else "RGB",target)
    edit.recompile_material(mat)
    lib.save_loaded_asset(mat)
    return mat


if not levels.load_level(level):
    raise RuntimeError("Missing traversal map")
material = paving_material()
for a in actors.get_all_level_actors():
    if a.get_actor_label().startswith(("Causeway","Court foundation","Road marker")):
        a.static_mesh_component.set_material(0,material)
# Geometry for the ridges is centred on the original encounter. Spread groups
# along the whole road with the spurs outside the player collision corridor.
folder="/Game/Vesper/RouteArt/GardenRidges"
if not lib.does_directory_exist(folder):
    task=unreal.AssetImportTask()
    task.filename=str(project/"Art"/"GardenRidges.glb")
    task.destination_path=folder
    task.automated=task.save=True
    tools.import_asset_tasks([task])
parts=[lib.load_asset(p) for p in lib.list_assets(folder)]
meshes=[m for m in parts if isinstance(m,unreal.StaticMesh) and any(n in m.get_name().lower() for n in ("limestone","pines"))]
if not meshes:
    # Export uses material names for meshes and localized import names for nodes.
    meshes=sorted([m for m in parts if isinstance(m,unreal.StaticMesh)],key=lambda m:m.get_bounds().sphere_radius,reverse=True)[:2]
if not meshes:
    raise RuntimeError("No distant ridge geometry imported")
if not any(a.get_actor_label().startswith("Distant ridge") for a in actors.get_all_level_actors()):
    for x,y,yaw in [(3500,-19000,8),(10400,21000,192),(20500,-22500,41)]:
        for m in meshes:
            a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x,y,-2300),unreal.Rotator(0,0,yaw))
            a.static_mesh_component.set_static_mesh(m)
            a.set_actor_label("Distant ridge " + m.get_name())
            a.set_actor_scale3d(unreal.Vector(2.45,2.45,2.2))
            a.set_actor_enable_collision(False)
if not levels.save_current_level():
    raise RuntimeError("Failed to save dressed pilgrimage")
(project / "Saved" / "PilgrimageDressed.json").write_text(json.dumps({"level": level, "ridge_meshes": len(meshes)}))
unreal.log("VESPER_ROUTE_DRESSED")
