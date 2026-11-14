"""Place the valley, scanned outcrops and wind-shaped pines around the three courts."""
import json
import math
from pathlib import Path
from random import Random
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
level = "/Game/Vesper/Maps/MountainPilgrimage"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
lib = unreal.EditorAssetLibrary
if not levels.load_level(level):
    raise RuntimeError("Missing pilgrimage map")


def mesh(name, source):
    folder = "/Game/Vesper/RouteArt/" + name
    if not lib.does_directory_exist(folder):
        task = unreal.AssetImportTask()
        task.filename, task.destination_path = str(source), folder
        task.automated = task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    for path in lib.list_assets(folder):
        obj = lib.load_asset(path)
        if isinstance(obj, unreal.StaticMesh):
            return obj
    raise RuntimeError("No static mesh imported from " + str(source))


def place(asset, label, x, y, z, yaw, scale, collision=False):
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x,y,z), unreal.Rotator(0,0,yaw))
    actor.static_mesh_component.set_static_mesh(asset)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.set_actor_label(label)
    actor.set_actor_enable_collision(collision)
    return actor


floor = mesh("MountainValley", project/"Art"/"MountainValley.glb")
pine = mesh("TrailPine", project/"SourceAssets"/"pine.glb")
rock = mesh("PassOutcrop", project/"SourceAssets"/"rock_face_01.glb")
existing = [a.get_actor_label() for a in actors.get_all_level_actors()]
if "Valley floor" not in existing:
    # A single convex hull would fill the stream depression and obstruct the road.
    body = floor.get_editor_property("body_setup")
    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    lib.save_loaded_asset(floor)
    place(floor, "Valley floor", 9700,0,0,0,(1,1,1),True)
    rng = Random(1928)
    path = [(0,0),(4200,0),(7600,1600),(11500,1600),(14800,-800),(19400,-800)]
    for (x,y),(xx,yy) in zip(path,path[1:]):
        dx,dy=xx-x,yy-y
        length=math.hypot(dx,dy)
        nx,ny=-dy/length,dx/length
        angle=math.degrees(math.atan2(dy,dx))
        for side in (-1,1):
            for i in range(12):
                t=(i+rng.uniform(0.12,0.88))/12
                offset=side*rng.uniform(1500,4800)
                tree_scale=rng.uniform(3.6,7.2)
                place(pine,"Mountain pine",x+dx*t+nx*offset,y+dy*t+ny*offset,
                      -410+95*tree_scale,rng.randrange(360),(tree_scale,)*3)
            for i in range(5):
                t=(i+0.5)/5
                offset=side*rng.uniform(460,780)
                place(rock,"Causeway bedrock",x+dx*t+nx*offset,y+dy*t+ny*offset,-460,
                      angle+side*90+rng.uniform(-14,14),(2.7,1.45,rng.uniform(1.1,1.5)))
    cube=lib.load_asset("/Engine/BasicShapes/Cube.Cube")
    stone=lib.load_asset("/Game/Vesper/RouteSurfaces/RoadStone")
    for x,y in [path[1],path[3],path[5]]:
        for i in range(32):
            stair=place(cube,"Valley stair",x,y-1400-32*i,-15-15*i,0,(2.5,0.38,0.31),True)
            stair.static_mesh_component.set_material(0,stone)

if not levels.save_current_level():
    raise RuntimeError("Valley save failed")
(project/"Saved"/"Valley.json").write_text(json.dumps({"map": level, "terrain_width_m":432,"pines":120,"outcrops":50}))
unreal.log("VESPER_VALLEY_SAVED")
