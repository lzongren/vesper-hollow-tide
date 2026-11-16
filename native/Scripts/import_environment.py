"""Run inside the Unreal Editor Python console, after fetching SourceAssets.

Imports only the pinned CC0 environment sources and records actual imported
object paths. This does not generate a playable level or pass visual acceptance.
Set VESPER_ASSET_ROOT when sources live outside native/SourceAssets.
"""
import importlib.util
import hashlib
import json
import os
from pathlib import Path

import unreal

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vesper_asset_sources", HERE / "assets.py")
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


def run():
    root = Path(os.environ.get('VESPER_ASSET_ROOT', str(HERE.parent / 'SourceAssets'))).resolve()
    raw = assets.LOCKFILE.read_bytes()
    lock = json.loads(raw)
    assets.validate_lock(lock)
    # Validate the complete source set before changing any editor assets.
    for entry in lock['assets']:
        for file in entry['files']:
            assets.fetch_file(root, entry, file, verify_only=True)
        assets.validate_gltf(root, entry)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    mesh_tools = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    report = {'status': 'import_in_progress', 'visual_quality': 'not_verified',
              'lock_sha256': hashlib.sha256(raw).hexdigest(), 'assets': []}
    for entry in lock['assets']:
        destination = f"/Game/External/PolyHaven/{entry['id']}"
        if unreal.EditorAssetLibrary.does_directory_exist(destination):
            raise RuntimeError(f'Import destination exists; inspect it before replacing: {destination}')
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', str(root / entry['id'] / entry['entry']))
        task.set_editor_property('destination_path', destination)
        task.set_editor_property('automated', True)
        task.set_editor_property('replace_existing', False)
        task.set_editor_property('save', True)
        asset_tools.import_asset_tasks([task])
        paths = list(task.get_editor_property('imported_object_paths'))
        meshes = []
        for path in paths:
            obj = unreal.EditorAssetLibrary.load_asset(path)
            if isinstance(obj, unreal.StaticMesh):
                settings = obj.get_editor_property('nanite_settings')
                settings.set_editor_property('enabled', True)
                mesh_tools.set_nanite_settings(obj, settings, True)
                if not unreal.EditorAssetLibrary.save_loaded_asset(obj):
                    raise RuntimeError(f'Could not save imported mesh: {path}')
                meshes.append(path)
        if not meshes:
            raise RuntimeError(f'No static meshes imported for {entry["id"]}; inspect the Interchange log')
        report['assets'].append({'id':entry['id'], 'objects':paths, 'meshes':meshes})
    report['status'] = 'imported_pending_visual_review'
    report_path = Path(unreal.Paths.project_saved_dir()) / 'Art' / 'import-report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    unreal.log(f'Environment import finished. Visual quality is still unverified. Report: {report_path}')


if __name__ == '__main__':
    run()
