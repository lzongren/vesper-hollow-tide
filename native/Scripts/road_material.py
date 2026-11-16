"""Construct the native stone material for the courts and causeway foundations."""
from pathlib import Path
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
root = "/Game/Vesper/RouteSurfaces"

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


def paving_material(rebuild=False):
    path = root + "/RoadStone"
    mat = lib.load_asset(path) if lib.does_asset_exist(path) else None
    if mat and not rebuild:
        return mat
    tex = {k:texture(k) for k in ("color","normal","rough")}
    edit = unreal.MaterialEditingLibrary
    if mat:
        edit.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset("RoadStone",root,unreal.Material,unreal.MaterialFactoryNew())
    def node(cls,x,y):
        return edit.create_material_expression(mat,cls,x,y)
    position = node(unreal.MaterialExpressionWorldPosition,-780,0)
    mask = node(unreal.MaterialExpressionComponentMask,-580,0)
    mask.set_editor_property("R", True)
    mask.set_editor_property("G", True)
    if not edit.connect_material_expressions(position,"",mask,""):
        raise RuntimeError("World position failed to connect to the XY mask")
    scale = node(unreal.MaterialExpressionMultiply,-390,0)
    scale.set_editor_property("ConstB", 1.0/220)
    if not edit.connect_material_expressions(mask,"",scale,"A"):
        raise RuntimeError("Failed to scale world-space paving coordinates")
    for i,(key,target) in enumerate([
        ("color",unreal.MaterialProperty.MP_BASE_COLOR),("normal",unreal.MaterialProperty.MP_NORMAL),
        ("rough",unreal.MaterialProperty.MP_ROUGHNESS)]):
        sample = node(unreal.MaterialExpressionTextureSample,-150,i*185)
        sample.set_editor_property("Texture", tex[key])
        if key=="normal":
            sample.set_editor_property("SamplerType", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        elif key=="rough":
            sample.set_editor_property("SamplerType", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        if not edit.connect_material_expressions(scale,"",sample,"UVs"):
            raise RuntimeError("Missing UVs for " + key)
        if not edit.connect_material_property(sample,"R" if key=="rough" else "RGB",target):
            raise RuntimeError("Failed to connect paving channel " + key)
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat):
        raise RuntimeError("Failed to save the paving material")
    return mat
