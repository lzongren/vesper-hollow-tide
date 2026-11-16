"""Keep Interchange instance parameters while compiling route-local shader variants."""

import unreal


def prepare(meshes, destination):
    lib = unreal.EditorAssetLibrary
    edit = unreal.MaterialEditingLibrary
    completed = {}

    def variant(source):
        path = source.get_path_name()
        if path in completed:
            return completed[path]
        if path.startswith("/Game/Vesper/"):
            result = source
        elif path.startswith("/InterchangeAssets/gltf/"):
            target = destination + "/" + source.get_name()
            result = (
                lib.load_asset(target)
                if lib.does_asset_exist(target)
                else lib.duplicate_asset(path, target)
            )
        else:
            raise RuntimeError("Unknown route shader " + path)
        if isinstance(result, unreal.MaterialInstanceConstant):
            parent = result.get_editor_property("parent")
            prepared = variant(parent)
            if parent != prepared:
                edit.set_material_instance_parent(result, prepared)
                edit.update_material_instance(result)
                if not lib.save_loaded_asset(result, only_if_is_dirty=False):
                    raise RuntimeError("Cannot save material instance " + path)
        elif isinstance(result, unreal.Material):
            changed = False
            for key in ("used_with_instanced_static_meshes", "used_with_nanite"):
                if not result.get_editor_property(key):
                    result.set_editor_property(key, True)
                    changed = True
            if changed:
                edit.recompile_material(result)
                if not lib.save_loaded_asset(result, only_if_is_dirty=False):
                    raise RuntimeError("Cannot save shader " + path)
        else:
            raise TypeError("Missing imported material " + path)
        completed[path] = result
        return result

    for mesh in meshes:
        for slot in mesh.static_materials:
            src = slot.material_interface
            if variant(src) != src:
                raise RuntimeError("Expected a project-owned material instance")
