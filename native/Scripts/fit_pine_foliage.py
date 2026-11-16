"""Apply a shared masked, light-transmitting needle material to the two native pine forms."""

from pathlib import Path
import json
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
lib = unreal.EditorAssetLibrary
edit = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
root = "/Game/Vesper/RouteArt/PineFoliage"
texture_name = "PineFascicles"
texture = (
    lib.load_asset(root + "/" + texture_name)
    if lib.does_asset_exist(root + "/" + texture_name)
    else None
)
if not texture:
    task = unreal.AssetImportTask()
    task.filename = str(project / "Art" / (texture_name + ".png"))
    task.destination_path = root
    task.automated = task.save = True
    tools.import_asset_tasks([task])
    texture = lib.load_asset(root + "/" + texture_name)
if not texture:
    raise RuntimeError("Cannot load pine fascicle atlas")
cutoff = 0.34
texture.set_editor_property("do_scale_mips_for_alpha_coverage", True)
texture.set_editor_property(
    "alpha_coverage_thresholds", unreal.Vector4(0, 0, 0, cutoff)
)
lib.save_loaded_asset(texture, only_if_is_dirty=False)

path = root + "/MountainNeedles"
mat = (
    lib.load_asset(path)
    if lib.does_asset_exist(path)
    else tools.create_asset(
        "MountainNeedles", root, unreal.Material, unreal.MaterialFactoryNew()
    )
)
edit.delete_all_material_expressions(mat)
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
mat.set_editor_property("two_sided", True)
mat.set_editor_property("opacity_mask_clip_value", cutoff)
foliage = next(
    getattr(unreal.MaterialShadingModel, k)
    for k in dir(unreal.MaterialShadingModel)
    if k.replace("_", "") == "MSMTWOSIDEDFOLIAGE"
)
mat.set_editor_property("shading_model", foliage)
sample = edit.create_material_expression(
    mat, unreal.MaterialExpressionTextureSample, -480, 0
)
sample.set_editor_property("texture", texture)


def output(node, pin, target):
    if not edit.connect_material_property(node, pin, target):
        raise RuntimeError("Unconnected foliage material property " + str(target))


prop = unreal.MaterialProperty
output(sample, "RGB", prop.MP_BASE_COLOR)
output(sample, "RGB", prop.MP_SUBSURFACE_COLOR)
output(sample, "A", prop.MP_OPACITY_MASK)
for channel, value, y in [
    (prop.MP_ROUGHNESS, 0.79, 220),
    (prop.MP_SPECULAR, 0.18, 350),
]:
    scalar = edit.create_material_expression(
        mat, unreal.MaterialExpressionConstant, -330, y
    )
    scalar.set_editor_property("r", value)
    output(scalar, "", channel)
edit.recompile_material(mat)
if not lib.save_loaded_asset(mat, only_if_is_dirty=False):
    raise RuntimeError("Could not save pine material")

meshes = []
for name in ("WindPine", "RidgePine"):
    mesh = lib.load_asset(
        "/Game/Vesper/RouteArt/MountainPines/MountainPines/StaticMeshes/" + name
    )
    slots = list(mesh.static_materials)
    indices = [
        i for i, s in enumerate(slots) if str(s.material_slot_name) == "Pine_needles"
    ]
    if len(indices) != 1:
        raise RuntimeError("Missing needle slot in " + name)
    slots[indices[0]].material_interface = mat
    mesh.set_editor_property("static_materials", slots)
    if not lib.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError("Could not save pine form " + name)
    meshes.append(mesh.get_path_name())
(project / "Saved" / "PineFoliage.json").write_text(
    json.dumps(dict(meshes=meshes, material=mat.get_path_name(), cutoff=cutoff))
)
unreal.log("VESPER_PINE_FOLIAGE_READY")
