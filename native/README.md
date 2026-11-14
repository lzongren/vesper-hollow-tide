# Native Unreal project

Mountain Pilgrimage links three courtyards with a 205.4-metre stone road. Two bends break the sightline between the belfry, garden and shrine. Each court has a staircase down to a 432 × 432 metre valley floor with outcrops and groups of mountain pines. UE 5.8.4 generated the level on Windows with an RTX 5080. The playable swordswoman wears an ivory magnolia coat with celadon lapels. An offset chignon holds a pale jade flower comb and three pearl drops. [Player fitting](../docs/runtime/magnolia-tailoring/) · [Waist streamers in motion](../docs/runtime/river-sash/) The fitting step uses skeleton transforms and locomotion animations from the locally installed Epic third-person template. The first courtyard hosts the Bellwarden. The Veiled Heron fights with paired sabres in the second courtyard. The Saint of Cinders guards the final reliquary. All three encounters also run in the browser prototype.

## Play the mountain route and court duels

Keep the checkout on a physical local drive outside OneDrive. The launcher checks the project path and places its filesystem cache under `%LOCALAPPDATA%\VesperDevelopment\DerivedDataCache`. Generated assets, map packages, logs and captures stay beside the local project. From the repository root in Windows PowerShell:

```powershell
.\native\Scripts\play_pilgrimage.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8'
```

Install the engine’s Templates and Feature Packs component. The first launch imports the repository’s GLBs and paving textures and creates the map. Subsequent launches reuse the saved level. Follow the road to the first lantern court for the Bellwarden, then continue around the bend to the moon gate. The Heron alternates a seven-feather fan, a committed lunge and close sabre cuts. Beyond the second bend, the Saint marks the ground under the player and sends an expanding ring across the final court. Use WASD to move and the mouse to look. Left click chains strikes, right click charges an attack, and Space steps in the movement direction or backwards from a standstill. The controller bindings are right shoulder, right trigger and the bottom face button. Generated project content stays on the machine. The project runs in standalone game mode through Unreal Editor and requires the editor installation.

[Saint of Cinders duel](../docs/runtime/cinder-duel/) · [Veiled Heron duel](../docs/runtime/heron-duel/) · [Slate forecourt in combat](../docs/runtime/slate-forecourt/) · [Mountain bell hall at 1440p](../docs/runtime/bell-hall/) · [Bellwarden costume and camera comparison](../docs/runtime/keeper-regalia/) · [Bellwarden combat captures and timings](../docs/runtime/belfry-duel/) · [Valley forest floor and ferns](../docs/runtime/valley-understory/) · [Evening light on the mountain route](../docs/runtime/mountain-evening/) · [Mountain pine gameplay comparison](../docs/runtime/mountain-pines/) · [Retaining walls and valley stair](../docs/runtime/mountain-masonry/) · [Procession road gameplay](../docs/runtime/procession-road/) · [Traversal measurements](../docs/runtime/mountain-pilgrimage/) · [Art direction and acceptance target](Art/quality-target.json)

The western pass includes layered limestone spurs, scanned foothill outcrops and planted pine stands. Tree locations drive a ground tint beneath the canopy. [Western pass gameplay views](../docs/runtime/western-pass/)

The mountain lighting pass uses the bundled HDR cloud deck for the sky and diffuse fill. Regenerate it with Python and NumPy using `python art/bake_mountain_sky.py native/Art/MountainOvercast.hdr`.

The optional pine mesh generator uses Python and Pillow. Run `python native/Scripts/mountain_pines.py public/textures native/Art/MountainPines.glb` to rebuild both tree forms and their embedded needle cutout. Normal game startup imports the bundled GLB.

Rebuild the retaining-wall bays and dressed treads with `python native/Scripts/retaining_mesh.py public/textures native/Art/CausewayAshlar.glb`. The map pass finds the exposed edges of the overlapping road and court foundations and leaves openings for each flight of stairs.

## Prepare sources

Use Python 3.10 or newer. No Python packages are required. Keep raw sources outside Git:

```powershell
python native/Scripts/assets.py --root C:/Art/VesperSources
python native/Scripts/assets.py --root C:/Art/VesperSources --verify-only
python -m unittest discover -s native/Tests -v
```

Each download must match the provider's pinned size and MD5. The receipt also records SHA-256 hashes and the exact lockfile digest. All glTF file dependencies must be local, pinned and present. These checks establish source integrity, not engine compatibility or visual quality. Use `--asset chinese_chandelier` to fetch one asset for an initial import trial.

The [lockfile](Art/assets.lock.json) includes source URLs and licenses. Poly Haven publishes these assets under [CC0](https://polyhaven.com/license). No Bloodborne, Wuchang, Epic sample or Fab assets are bundled or downloaded by these scripts.

## Optional Poly Haven source import

The optional source importer targets Unreal 5.8. The editor must include Python scripting, Editor Scripting Utilities and glTF Interchange support.

Set `VESPER_ASSET_ROOT` to the source directory **before launching the editor**, then open `Vesper.uproject`. In the editor Python console, execute the import script using its absolute path:

```python
exec(compile(open("C:/path/to/vesper/native/Scripts/import_environment.py", encoding="utf-8").read(), "C:/path/to/vesper/native/Scripts/import_environment.py", "exec"), {"__name__": "__main__", "__file__": "C:/path/to/vesper/native/Scripts/import_environment.py"})
```

The importer verifies the complete source set, imports under `/Game/External/PolyHaven`, requests Nanite for imported static meshes, and records actual object paths in `Saved/Art/import-report.json`. It refuses an existing destination to avoid silently replacing edited art. After an interrupted import, inspect and remove only the generated import folders before retrying. Engine import behavior and Nanite setup remain untested until this runs in the editor.

`SourceAssets`, generated `Content/External`, caches and binaries are ignored. Keep the lockfile and source scripts in Git; do not commit raw asset caches or account information.

## Remaining work and acceptance

1. Evaluate the optional source pack in the editor and inspect scale, normal maps and shadows.
2. Build an original Chinese temple arena with coherent period-inspired architecture, layered surfaces, believable vegetation and composed lighting. A mixture of downloaded models is not a finished art direction.
3. Create the player and three boss designs, rig and animate locomotion and combat; implement their readable telegraphs and physical contact.
4. Port combat rules, camera, input, UI and adaptive audio; complete all three encounters and package a runnable build.
5. Capture unretouched 2560×1440 gameplay and frame times on the RTX 5080, including close views, moving camera and full fights. Compare the actual result with the requested reference, and obtain visual acceptance.

The browser screenshots in the root README document the earlier prototype. They are not evidence for this rebuild, and title artwork is not gameplay.

The original [Tide Bell GLB](../public/models/tide-bell.glb) is shared with the playable browser encounter. To inspect it in Unreal, import the GLB as a static mesh using Interchange with material and texture import enabled. The asset uses glTF meters. Native import and native combat placement still need editor verification.

The [Saint's ring staff](Art/SaintsRingStaff.glb) uses the playable staff geometry in metres. Its six ring nodes retain separate pivots at the tops of the hoops so they can swing on the bronze rails. The export contains four named PBR material slots with base factors. The court's shared texture maps and the runtime spring simulation stay in the browser project. Regenerate the asset from the repository root with `npx tsx art/export_ring_staff.ts`. The native staff follows the right hand of the fitted Saint. The six ring pivots are baked into that fitting.

The [Heron's bridal headpiece](Art/HeronBridalMask.glb) carries the pierced porcelain face, coiffure, metal hairpins and trim, garnets and silk side veils from the playable encounter. Six meshes retain their material assignments, including the openwork crown and pearls. The porcelain carries the embedded painted glaze with glTF-oriented UVs. Silk and metal use base material factors. Regenerate it with `npx tsx art/export_heron_mask.ts`. In the native encounter the mask and crown are fitted to the head bone, with a dedicated glazed porcelain surface.

The [moon gate porch](Art/MoonGatePorch.glb) carries the playable garden's hipped roof, posts, carved brackets and hanging lamp. Five mesh groups have named material slots. The model units are metres, the origin is at ground level, and the court faces +Z in glTF coordinates. The export uses base material factors. The browser's scanned textures, point light, surrounding wall and bridge are separate. Run `npx tsx art/export_moon_gate.ts` to rebuild it. The traversal builder imports this porch into the second court.

The [pilgrim's bamboo hat](Art/PilgrimRainHat.glb) and [empty lacquer scabbard](Art/PilgrimScabbard.glb) use the playable travel gear geometry in local metres. The hat origin is the brim centre. The scabbard origin is the open throat, with the tip below it. Run `npx tsx art/export_pilgrim_travel_gear.ts` to rebuild them. The palm cape follows the browser cloth simulation. Its native version is skinned to the pilgrim and uses the source strip colours baked into texture maps. To regenerate the complete neutral mantle with colour, normal and roughness maps, install Pillow for the authoring Python interpreter and run `npx tsx art/export_pilgrim_mantle.ts`. Set `PYTHON` to select that interpreter. [Native cape gameplay](../docs/runtime/palm-mantle/)

The [west water gallery](Art/WestWaterGallery.glb) has five open bays, recessed lattice, ribbed lanterns and overlapping courses of glazed tiles. Run `npx tsx art/export_water_gallery.ts` for the local-space mesh with named material slots. The playable browser court places it beside the lotus pool. The native route uses the gallery beside the road and on either side of the final shrine.

The [Heron's paired sabres](Art/HeronSabres.glb) include grasping hands, wrapped hilts, bronze furniture and beveled steel. The two wrist nodes carry three named glTF animation clips in actor-local metres. Their timing and orientation are sampled from the gameplay wrist targets. The browser applies arm IK to those targets and clamps them to each limb's reach. The export contains the wrist tracks, without the full character skeleton. Run `npx tsx art/export_heron_sabres.ts` to rebuild it. The native second-court encounter fits the paired sabres to the combat skeleton’s wrists and plays the native strike animations.

The [mountain pass beacon](Art/MountainPassBeacon.glb) is the three-storey landmark on the garden's western ridge. It preserves the four mesh groups for stone, timber, tiles and the lit paper core. Regenerate it with `npx tsx art/export_ridge_pavilion.ts`. The local origin lies in the footing and units are metres. The surrounding ridges are generated separately by the web game. Native import and lighting still require verification.

The [Garden Ridges GLB](Art/GardenRidges.glb) includes the eight limestone spurs, their summit pines, the mountain pass beacon in position, and the embedded limestone albedo. The courtyard origin is at the centre of the arrangement. Six mesh groups contain 138,100 triangles. Eight separately weathered faces share a 4096 × 4096 color atlas. Regenerate it with `npx tsx art/export_karst.ts`. The height-dependent mist and fine bump response are implemented by the browser renderer. Native import is pending.

The [pilgrim's jian](Art/PilgrimJian.glb) contains 7,716 triangles in four PBR material groups. The blade points along local +Y, with the wrist at the origin and the point at 1.43 metres. Regenerate it with `npx tsx art/export_pilgrim_jian.ts`. The short exposure at the moving point is a browser effect. Unreal import and attachment remain pending.

The [shrine lotus portal](Art/ShrineLotusPortal.glb) contains the dressed arch, carved leaves, open bronze crest, jambs and five staggered stair courses. It has 19,232 triangles across limestone and bronze. The threshold centre is the native placement pivot. Stone tint is in COLOR_0. UVs are prepared for the rock and metal scan sets in public/textures. Those maps must be assigned when importing the mesh. Regenerate it with `npx tsx art/export_shrine_portal.ts`. The native shrine uses the fitted arch with lit stone and bronze surfaces.

The [guardian and paired dragons](../public/models/cinder-relief.glb) is the same self-contained GLB loaded by the playable shrine. Its 10.8 m × 7.8 m face carries 67,200 triangles, a painted albedo and a local roughness/metalness map. Import it as one static mesh with material import enabled. Local +Z points into the court. The lamps and arch masonry are separate. Rebuild with Python, NumPy and Pillow using `python3 art/shrine_relief.py`. In the native shrine, the relief stands behind the lotus arch between two warm lights.

The [Saint’s bronze head and mandorla](Art/CinderVotiveHead.glb) use the same sculpted geometry as the third browser encounter. The face and halo have separate pivots. The browser attaches the face to the head bone and drives the ember material from combat state. Regenerate the static reference with `npx tsx art/bake_cinder_head.ts`. In the native fitting the face follows the head and the mandorla follows the upper spine.

The three court pavements are exported at gameplay scale with registered color, normal and metallic/roughness images embedded in each GLB. The material uses vertex color for wear and individual stone tone. The browser adds dynamic water reflections and contact shading at runtime. Rebuild the maps with `python3 art/inlay_surfaces.py` and the geometry with `npx tsx art/export_flagstone_courts.ts`. The native traversal builder imports these three courts. [Belfry](Art/BelfryFlagstones.glb) · [Heron](Art/HeronFlagstones.glb) · [Cinder](Art/CinderFlagstones.glb)

The [Saint’s skinned body](../public/models/cinder-ascetic.glb) embeds its color, normal, roughness, emission and two hand gestures. CastOpen and CastClench are relative morphs on the left fingers. The browser blends them with the attack state before applying the hand bone transform. The [paired armour](Art/CinderArmGuards.glb) uses separate upper-arm and forearm fittings in neutral actor coordinates. The native fitting uses the skinned body, paired armour, a separate brocade stole and combat skeleton. The finger morphs are specific to the browser build.

The [painted belfry front](Art/BelfryPaintedFront.glb) groups the columns, bracket sets, dragon-painted beams, six paper screen panels, rails and exposed rafter ends. It contains 10,966 triangles across eight material meshes. The four embedded JPEGs retain the browser artwork and stone and timber scans. Its local coordinates match the existing belfry hall; the browser places that hall at (0, 0, −24) and applies a uniform scale of 1.7. Rebuild with `python3 art/belfry_frieze.py` and `npx tsx art/export_belfry_front.ts`. The traversal builder places this front in the first court.

The Bellwarden’s matching shoulder fittings have independent socket origins and five animated layers each. The crown stays close to the collar and the four lower lames follow progressively more of the upper arm’s turn. Each glTF includes a fitting lift clip and the sculpted bronze, lacquer and lining materials. The game derives its actual poses from the solved arm during each attack. The exports use scalar PBR materials and omit the browser scan textures. Rebuild with `npx tsx art/export_bell_pauldrons.ts`. Import and playback in Unreal remain unverified. [Right fitting](Art/BellwardenRightPauldron.glb) · [Left fitting](Art/BellwardenLeftPauldron.glb)

The [shrine cliff and votive path](Art/ShrineCliffWalk.glb) contains the playable shrine’s mountain ring, summit trees and west-face gallery. Its deck follows the cliff mesh, with crossbeams above a second row of stone anchors. The two sheltered bays carry suspended lamps. Regenerate the atlas with `python art/bake_karst_faces.py` (NumPy and Pillow), then run `npx tsx art/export_karst.ts shrine`. The native shrine places the imported cliff walk behind the guardian relief.

[The Falling Prayers animation](Art/CinderSealCast.glb) includes the ascetic skin, its original animation, and a second clip sampled at 60 Hz from the playable arm solver and finger poses. It contains three local rotation tracks and two finger morph weights on the skinned mesh. The clip follows a first-phase cast. The rings, wrist beads, particle volume, combat camera and hazard timing remain runtime components. Regenerate with `npx tsx art/export_cinder_cast.ts`. Engine import and retargeting remain unverified.
