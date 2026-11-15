# 松壑山脚

The six fallen boulders use Kless Gyzen’s [Rock Moss Set 01](https://polyhaven.com/a/rock_moss_set_01). The fans use [Rock Ground 02](https://polyhaven.com/a/rock_ground_02). Grass and flowers come from [Grass Medium 02](https://polyhaven.com/a/grass_medium_02) and [Dandelion 01](https://polyhaven.com/a/dandelion_01). The inscribed rock reuses the route’s [Rock Face 01](https://polyhaven.com/a/rock_face_01). These Poly Haven scans are [CC0](https://polyhaven.com/license).

“松壑” is original text for this game. The letterforms are rasterized from [Ma Shan Zheng](https://github.com/google/fonts/tree/main/ofl/mashanzheng), licensed under the SIL Open Font License. The inscription baker projects the characters into the scan's UV islands and indents their edges in the tangent normal map. The game needs only the finished textures. The wind loop is original synthesis.

## Rebuilding the source art

Use Python 3 with Pillow and NumPy. Download models and texture maps from the links above. Keep working copies on a local physical drive outside OneDrive.

1. Place the 2K glTF from Rock Moss Set 01 directly under a source folder with its accompanying BIN and textures. Name the scene `rock_moss_set_01.gltf`. Place the 2K JPEG maps from Rock Ground 02 beside it as `Diffuse.jpg`, `AO.jpg`, `Rough.jpg`, and `nor_dx.jpg`.
2. Place each plant's 1K glTF download in a subfolder named after its asset ID. Retain all dependencies and name each glTF after the ID. Save the single-channel 1K Alpha map beside its glTF as `opacity`. The packer combines this with the diffuse JPEG and writes the normalized blade height into the green vertex channel for wind.
3. From the checkout, run the following commands with the paths to those inputs.

```sh
python art/shrine_scree_assets.py /path/to/sources native/Art/ShrineTalus
python art/pine_ravine_inscription.py /path/to/SourceAssets/rock_face_01.glb /path/to/MaShanZheng-Regular.ttf native/Art/ShrineTalus
python art/ravine_wind.py
```

The map pass generates the fan mesh beside the local Unreal project and instances the plants and stones on its surface. The native launcher configures the local cache. [Game-window captures and traversal](../../../docs/runtime/shrine-talus/)
