"""Lay fitted grey slabs and cast bronze votive lanterns along the pilgrimage."""
import json
import math
import runpy
from pathlib import Path
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
lib = unreal.EditorAssetLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
level = "/Game/Vesper/Maps/MountainPilgrimage"


def import_meshes(name):
    folder = "/Game/Vesper/RouteArt/" + name
    if not lib.does_directory_exist(folder):
        task = unreal.AssetImportTask()
        task.filename = str(project / "Art" / (name + ".glb"))
        task.destination_path = folder
        task.automated = task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes = []
    for path in lib.list_assets(folder):
        if str(lib.find_asset_data(path).asset_class_path.asset_name) == "StaticMesh":
            mesh = lib.load_asset(path)
            settings = mesh.get_editor_property("nanite_settings")
            settings.set_editor_property("enabled", False)
            mesh.set_editor_property("nanite_settings", settings)
            if not lib.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError("Failed to save " + path)
            meshes.append(mesh)
    if not meshes:
        raise RuntimeError("Missing geometry " + name)
    return meshes


def place(mesh, label, x, y, z, yaw, scale):
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x,y,z), unreal.Rotator(0,0,yaw))
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_label(label)
    a.set_actor_scale3d(unreal.Vector(*scale))
    a.set_actor_enable_collision(False)


if not levels.load_level(level):
    raise RuntimeError("Missing pilgrimage")
runpy.run_path(str(project/"Scripts"/"road_material.py"))["paving_material"](rebuild=True)
paving = import_meshes("ProcessionPaving")
lantern = import_meshes("ProcessionLantern")
for a in actors.get_all_level_actors():
    tag = a.get_actor_label()
    if tag.startswith(("Road marker","Procession slab","Procession lantern","Votive light")):
        actors.destroy_actor(a)
    elif isinstance(a, unreal.DirectionalLight):
        a.set_actor_rotation(unreal.Rotator(0,-17,139), False)
        a.light_component.set_editor_property("intensity", 1.35)
        a.light_component.set_light_color(unreal.LinearColor(.63,.76,1,1))
    elif isinstance(a, unreal.ExponentialHeightFog):
        fog = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
        fog.set_editor_property("fog_density", .034)
        fog.set_editor_property("fog_height_falloff", .19)
        fog.set_editor_property("start_distance", 650)
        fog.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(.07,.12,.18,1))

points = [(0,0),(4200,0),(7600,1600),(11500,1600),(14800,-800),(19400,-800)]
tiles = lamps = 0
for section, ((x,y),(xx,yy)) in enumerate(zip(points,points[1:])):
    dx, dy = xx-x, yy-y
    length = math.hypot(dx,dy)
    yaw = math.degrees(math.atan2(dy,dx))
    count = round(length/830)
    for i in range(count):
        t=(i+.5)/count
        # Slab tops sit above the plain collision deck but beneath the court inlays.
        for mesh in paving:
            place(mesh, "Procession slab", x+dx*t,y+dy*t,-1.5,yaw+180*(i%2),(length/count/830,1,1))
        tiles+=1
    for i,t in enumerate((.075,.42,.78)):
        for side in (-1,1):
            # A broken cadence reveals the gallery and forest between lamps.
            if i==1 and (section+side)%3==0:
                continue
            lx,ly=x+dx*t-side*dy/length*391,y+dy*t+side*dx/length*391
            for mesh in lantern:
                place(mesh,"Procession lantern",lx,ly,-2,yaw+side*17,(1,1,1))
            light=actors.spawn_actor_from_class(unreal.PointLight,unreal.Vector(lx,ly,194))
            light.set_actor_label("Votive light")
            c=light.light_component
            c.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
            c.set_editor_property("intensity", 100)
            c.set_editor_property("attenuation_radius", 600)
            c.set_editor_property("cast_shadows", False)
            c.set_light_color(unreal.LinearColor(1,.38,.12,1))
            lamps+=1
if not levels.save_current_level():
    raise RuntimeError("Cannot save dressed causeway")
(project/"Saved"/"Procession.json").write_text(json.dumps({"level":level,"paving_modules":tiles,"lanterns":lamps}))
unreal.log("VESPER_PROCESSION_SAVED")
