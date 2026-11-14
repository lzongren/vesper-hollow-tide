# Native visual rebuild — work in progress

The browser prototype did not meet the requested visual quality. This directory starts a Windows / RTX 5080 Unreal project aimed at realistic, richly detailed Chinese dark fantasy, with visual quality exceeding Bloodborne and three complete boss encounters. **That target is not achieved.** There is no playable native level or packaged game yet.

## What exists

- A Blueprint-only Unreal project descriptor and proposed Lumen, Nanite, virtual shadow map and TSR settings. These have not been opened or validated in Unreal.
- Seven pinned CC0 environment sources from Poly Haven, approximately 307.5 MB: stone construction, sculptural detail, doors, ironwork, a Chinese chandelier and rocks. This is a source-material batch, not a finished Chinese architectural kit. Character art and authored combat animations are still missing.
- A reproducible downloader, integrity checks and an unexecuted Unreal editor importer.
- An explicit [visual acceptance target](Art/quality-target.json). Asset downloads, unit tests and renderer configuration cannot satisfy that target.

The existing browser combat in `../src/combat.ts` remains the behavioral reference for the Bellwarden, Veiled Heron and Saint of Cinders. Those fights have **not** been ported into this project.

## Prepare sources

Use Python 3.10 or newer. No Python packages are required. Keep raw sources outside Git:

```powershell
python native/Scripts/assets.py --root C:/Art/VesperSources
python native/Scripts/assets.py --root C:/Art/VesperSources --verify-only
python -m unittest discover -s native/Tests -v
```

Each download must match the provider's pinned size and MD5. The receipt also records SHA-256 hashes and the exact lockfile digest. All glTF file dependencies must be local, pinned and present. These checks establish source integrity, not engine compatibility or visual quality. Use `--asset chinese_chandelier` to fetch one asset for an initial import trial.

The [lockfile](Art/assets.lock.json) includes source URLs and licenses. Poly Haven publishes these assets under [CC0](https://polyhaven.com/license). No Bloodborne, Wuchang, Epic sample or Fab assets are bundled or downloaded by these scripts.

## Open and import — engine verification pending

Install Unreal through the official Epic Games Launcher using your own account. The project currently targets 5.8; verify engine and plugin compatibility before treating it as a working baseline. The editor must include Python scripting, Editor Scripting Utilities and glTF Interchange support.

Set `VESPER_ASSET_ROOT` to the source directory **before launching the editor**, then open `Vesper.uproject`. In the editor Python console, execute the import script using its absolute path:

```python
exec(compile(open("C:/path/to/vesper/native/Scripts/import_environment.py", encoding="utf-8").read(), "C:/path/to/vesper/native/Scripts/import_environment.py", "exec"), {"__name__": "__main__", "__file__": "C:/path/to/vesper/native/Scripts/import_environment.py"})
```

The importer verifies the complete source set, imports under `/Game/External/PolyHaven`, requests Nanite for imported static meshes, and records actual object paths in `Saved/Art/import-report.json`. It refuses an existing destination to avoid silently replacing edited art. After an interrupted import, inspect and remove only the generated import folders before retrying. Engine import behavior and Nanite setup remain untested until this runs in the editor.

`SourceAssets`, generated `Content/External`, caches and binaries are ignored. Keep the lockfile and source scripts in Git; do not commit raw asset caches or account information.

## Remaining work and acceptance

1. Install and launch the engine, execute the importer, and inspect scale, normals, material channels, Nanite and shadow behavior in a real test map.
2. Build an original Chinese temple arena with coherent period-inspired architecture, layered surfaces, believable vegetation and composed lighting. A mixture of downloaded models is not a finished art direction.
3. Create the player and three boss designs, rig and animate locomotion and combat; implement their readable telegraphs and physical contact.
4. Port combat rules, camera, input, UI and adaptive audio; complete all three encounters and package a runnable build.
5. Capture unretouched 2560×1440 gameplay and frame times on the RTX 5080, including close views, moving camera and full fights. Compare the actual result with the requested reference, and obtain visual acceptance.

The browser screenshots in the root README document the earlier prototype. They are not evidence for this rebuild, and title artwork is not gameplay.

The original [Tide Bell GLB](../public/models/tide-bell.glb) is shared with the playable browser encounter. To inspect it in Unreal, import the GLB as a static mesh using Interchange with material and texture import enabled. The asset uses glTF meters. Native import and native combat placement still need editor verification.

The [Saint's ring staff](Art/SaintsRingStaff.glb) uses the playable staff geometry in metres. Its six ring nodes retain separate pivots at the tops of the hoops so they can swing on the bronze rails. The export contains four named PBR material slots with base factors. The court's shared texture maps and the runtime spring simulation stay in the browser project. Regenerate the asset from the repository root with `npx tsx art/export_ring_staff.ts`. Import and animation inside Unreal still need editor verification.

The [Heron's bridal headpiece](Art/HeronBridalMask.glb) carries the pierced porcelain face, coiffure, metal hairpins and trim, garnets and silk side veils from the playable encounter. Five separate meshes retain their material assignments. The export uses base material factors for silk and metal. Regenerate it with `npx tsx art/export_heron_mask.ts`. Editor import and fitting to a native head joint are pending.

The [moon gate porch](Art/MoonGatePorch.glb) carries the playable garden's hipped roof, posts, carved brackets and hanging lamp. Five mesh groups have named material slots. The model units are metres, the origin is at ground level, and the court faces +Z in glTF coordinates. The export uses base material factors. The browser's scanned textures, point light, surrounding wall and bridge are separate. Run `npx tsx art/export_moon_gate.ts` to rebuild it. Unreal import and in-editor lighting are pending.

The [Heron's paired sabres](Art/HeronSabres.glb) include grasping hands, wrapped hilts, bronze furniture and beveled steel. The two wrist nodes carry three named glTF animation clips in actor-local metres. Their timing and orientation are sampled from the gameplay wrist targets. The browser applies arm IK to those targets and clamps them to each limb's reach. The export contains the wrist tracks, without the full character skeleton. Run `npx tsx art/export_heron_sabres.ts` to rebuild it. Import and retargeting in Unreal remain pending.
