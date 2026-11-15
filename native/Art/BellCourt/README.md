# Bell-court guardian casting

The geometry of the lion and its decorated pedestal derives from **Chinese guardian lion**, a RangeVision Spectrum scan of a small porcelain figure by **rvscanners**. It is distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). [Original scan and author](https://sketchfab.com/3d-models/chinese-guardian-lion-afdb632cc23f4c0c9bbaa1100010039f) · [Archived source mesh in Objaverse](https://huggingface.co/datasets/allenai/objaverse/resolve/main/glbs/000-129/afdb632cc23f4c0c9bbaa1100010039f.glb)

The adaptation welds the source patches, reduces the mesh, rotates and enlarges the sculpture, assigns bronze, patina and polished edges, and adds a two-course stone footing. The original object is porcelain. The patina and monumental scale are fictional. The same casting stands on either side of the first courtyard entrance.

To regenerate the bundled asset, install NumPy, SciPy, trimesh Pillow and fast-simplification, then run `python art/cast_gate_lion.py source.glb native/Art/BellCourt/GateLion.glb`. The baker verifies the source SHA-256. Unreal reads the bundled GLB directly.

The fine corrosion mask derives from the colour channel of [Poly Haven’s rusty_metal_02](https://polyhaven.com/a/rusty_metal_02) (CC0). The game projects it in three axes and uses it to vary bronze colour, roughness and metallic response.

The court ambience is original synthesized audio. A 31-second loop combines two bands of gusting pine noise with six irregular bronze wind-bell strikes. It is a spatial mono source under the hall eaves. Rebuild it with `python art/bell_court_wind.py` and NumPy.

The rain gallery is original timber and tile geometry. The two-egret wall uses an original ImageGen grayscale sculpt guide showing egrets, reeds and plum blossom. The game renders the birds as a 257 × 129 displaced mesh with tangent-space chisel marks and a clay finish. To rebake the bundled relief maps, run `python art/egret_brick.py /path/to/SourceAssets` with Pillow and NumPy. The existing rock-color image from the project's asset manifest supplies the grain. The ordinary launcher runs `fit_bell_gallery.py` to construct and place the roof and screen.
