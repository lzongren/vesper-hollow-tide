"""Build the three-court mountain route in an isolated Vesper editor project."""
import json
import math
from pathlib import Path

import unreal

PROJECT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
LEVEL = "/Game/Vesper/Maps/MountainPilgrimage"
ART = "/Game/Vesper/RouteArt"
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
library = unreal.EditorAssetLibrary
v = unreal.Vector
rotation = lambda yaw: unreal.Rotator(0, 0, yaw)


def import_parts(name):
    folder = f"{ART}/{name}"
    paths = library.list_assets(folder) if library.does_directory_exist(folder) else []
    if not paths:
        task = unreal.AssetImportTask()
        task.filename = str(PROJECT / "Art" / f"{name}.glb")
        task.destination_path = folder
        task.automated = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = library.list_assets(folder)
    parts = [library.load_asset(path) for path in paths]
    meshes = [part for part in parts if isinstance(part, unreal.StaticMesh)]
    if not meshes:
        raise RuntimeError(f"Missing imported geometry in {folder}")
    return meshes


def place(asset, location, yaw, scale, label):
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, v(*location), rotation(yaw))
    actor.static_mesh_component.set_static_mesh(asset)
    actor.set_actor_scale3d(v(*scale))
    actor.set_actor_label(label)
    return actor


def build():
    exists = library.does_asset_exist(LEVEL)
    names = ["WestWaterGallery", "MountainPassBeacon", "MoonGatePorch", "BelfryPaintedFront",
             "ShrineLotusPortal", "BelfryFlagstones", "HeronFlagstones", "CinderFlagstones"]
    meshes = {name: import_parts(name) for name in names}
    if exists:
        if not levels.load_level(LEVEL) or any(isinstance(a, unreal.StaticMeshActor) for a in actors.get_all_level_actors()):
            raise RuntimeError(f"An existing authored map occupies {LEVEL}")
    elif not levels.new_level(LEVEL):
        raise RuntimeError("Cannot create pilgrimage map")
    cube = library.load_asset("/Engine/BasicShapes/Cube.Cube")
    def piece(name, x, y, z, yaw=0, scale=1):
        for mesh in meshes[name]:
            place(mesh, (x,y,z), yaw, (scale,)*3, name)
    def block(x,y,z,length,width,height,yaw,label):
        return place(cube,(x,y,z),yaw,(length/100,width/100,height/100),label)
    # Metres of traversable road, with a dogleg that hides the next court.
    points = [(0,0),(4200,0),(7600,1600),(11500,1600),(14800,-800),(19400,-800)]
    route_length = 0
    for i, ((x,y),(xx,yy)) in enumerate(zip(points,points[1:])):
        dx,dy=xx-x,yy-y
        length=math.hypot(dx,dy)
        route_length+=length
        angle=math.degrees(math.atan2(dy,dx))
        block((x+xx)/2,(y+yy)/2,-54,length+45,830,100,angle,"Causeway")
        nx,ny=-dy/length,dx/length
        for side in [-1,1]:
            for j in range(1,int(length//600)):
                u=j*600/length
                block(x+dx*u+nx*side*435,y+dy*u+ny*side*435,25,55,75,85,angle,"Road marker")
        if i in (1,3):
            piece("WestWaterGallery",(x+xx)/2+nx*700,(y+yy)/2+ny*700,0,angle)
    for (x,y),seal,portal in zip([points[1],points[3],points[5]],
            ["BelfryFlagstones","HeronFlagstones","CinderFlagstones"],
            ["BelfryPaintedFront","MoonGatePorch","ShrineLotusPortal"]):
        block(x,y,-62,2920,2800,118,0,"Court foundation")
        piece(seal,x,y,5,0,2.0)
        piece(portal,x+900,y,8,180)
    for x,y,z in [(2200,-2300,-10),(8500,4400,110),(16600,-3700,60)]:
        piece("MountainPassBeacon",x,y,z,15,1.3)
    start=actors.spawn_actor_from_class(unreal.PlayerStart,v(200,0,120),rotation(0))
    start.set_actor_label("Pilgrim arrival")
    for cls in (unreal.SkyAtmosphere,unreal.SkyLight,unreal.ExponentialHeightFog):
        actors.spawn_actor_from_class(cls,v(0,0,0))
    light=actors.spawn_actor_from_class(unreal.DirectionalLight,v(0,0,3000),unreal.Rotator(0,-27,-48))
    light.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light",True)
    light.light_component.set_editor_property("intensity",4.5)
    light.light_component.set_light_color(unreal.LinearColor(1.0,0.76,0.56,1.0))

    if not levels.save_current_level():
        raise RuntimeError("Failed to save pilgrimage map")
    report = {"map":LEVEL,"route_length_metres":round(route_length/100,1),"court_count":3,
              "mesh_parts":{k:len(vv) for k,vv in meshes.items()}}
    (PROJECT/"Saved"/"Pilgrimage.json").write_text(json.dumps(report,indent=2))
    unreal.log(f"Vesper pilgrimage built: {report}")


if __name__ == "__main__":
    build()
