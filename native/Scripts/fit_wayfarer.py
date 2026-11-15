"""Install the magnolia-coated player on the existing combat pawn blueprint."""

from pathlib import Path
import json
import sys
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
sys.path.insert(0, str(project / "Scripts"))
from build_bellwarden import mesh_for, fit, lib, combat
from keeper_materials import surface
from sash_material import silk_motion
from wayfarer_skin import complexion
from camellia_materials import cornea, hair_roots, lashes

mesh = mesh_for("ZhaoyueHaitang", "pilgrim.glb", armed=True, wayfarer=True)
if not any(
    str(name).lower().endswith("blink") for name in mesh.get_all_morph_target_names()
):
    raise RuntimeError("The fitted swordswoman is missing her eyelid morph")
bp = lib.load_asset(combat + "BP_CombatCharacter")
reference = unreal.get_default_object(
    bp.generated_class()
).mesh.skeletal_mesh_asset.skeleton
mesh.skeleton.set_editor_property("compatible_skeletons", [reference])
lib.save_loaded_asset(mesh.skeleton, only_if_is_dirty=False)
root = mesh.get_path_name().split("/SkeletalMeshes/")[0]
slots = list(mesh.materials)
finishes = {
    "LinenGaiters": (0.02, 0.74),
    "MourningSage": (0.08, 0.65),
    "SpectreIvory": (0.10, 0.51),
    "RoseBinding": (0.03, 0.70),
    "ChasedBrass": (0.65, 0.40),
}


def tint_weave(mat, color):
    edit = unreal.MaterialEditingLibrary
    prop = unreal.MaterialProperty.MP_BASE_COLOR
    texture = edit.get_material_property_input_node(mat, prop)
    if isinstance(texture, unreal.MaterialExpressionMultiply):
        return
    multiply = edit.create_material_expression(
        mat, unreal.MaterialExpressionMultiply, -100, 0
    )
    dye = edit.create_material_expression(
        mat, unreal.MaterialExpressionConstant3Vector, -350, -120
    )
    dye.set_editor_property("constant", unreal.LinearColor(*color, 1))
    if not (
        edit.connect_material_expressions(texture, "RGB", multiply, "A")
        and edit.connect_material_expressions(dye, "", multiply, "B")
        and edit.connect_material_property(multiply, "", prop)
    ):
        raise RuntimeError("Could not dye " + mat.get_name())
    edit.recompile_material(mat)
    lib.save_loaded_asset(mat, only_if_is_dirty=False)


for slot in slots:
    name = str(slot.material_slot_name)
    if name in ("WayfarerSkin", "NecklineSkin"):
        slot.material_interface = complexion(root)
    elif name == "WetIris":
        slot.material_interface = cornea(root)
    elif name == "LashFringe":
        slot.material_interface = lashes(root)
    elif name in finishes:
        metal, rough = finishes[name]
        slot.material_interface = surface(root, name + "Surface", name, metal, rough)
        if name == "MourningSage":
            tint_weave(slot.material_interface, (0.41, 0.60, 0.50))
        elif name == "LinenGaiters":
            tint_weave(slot.material_interface, (0.51, 0.50, 0.46))
    elif name == "RiverBrocade":
        slot.material_interface = silk_motion(root)
    elif name == "WillowLocks":
        slot.material_interface = surface(
            root, "CombedWillowHair", name, 0, 0.48, cutout=True, specular=0.24
        )
    elif name == "TempleStrands":
        slot.material_interface = hair_roots(root)
    elif name == "InkHair":
        slot.material_interface = surface(
            root, "BrushedInk", name, 0, 0.59, specular=0.21
        )
    elif name == "Pilgrim_0":
        slot.material_interface = surface(
            root, "TravelBoots", "TravelLeather", 0.06, 0.73
        )
    elif name.startswith("SwordCase_"):
        gilt = name in ("SwordCase_1", "SwordCase_3")
        slot.material_interface = surface(
            root,
            "OldBrass" if gilt else "DarkScabbard",
            "ChasedBrass" if gilt else "TravelLeather",
            0.65 if gilt else 0.09,
            0.47 if gilt else 0.59,
        )
mesh.set_editor_property("materials", slots)
lib.save_loaded_asset(mesh, only_if_is_dirty=False)
fit("BP_CombatCharacter", "BP_BelfryPilgrim", mesh, {})
(project / "Saved" / "WayfarerOutfit.json").write_text(
    json.dumps({"mesh": mesh.get_path_name(), "revision": 25})
)
unreal.log("VESPER_WAYFARER_READY")
