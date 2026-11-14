# Sanctuary courts

The screenshots show the three playable encounters at 2560 × 1440 on Windows Edge using the RTX 5080. Each was captured through the encounter selector with the normal HUD, movement, attack and dodge inputs. The side view follows a strafe around the Bellwarden. The Heron clip follows the player's camera during an exchange.

## Runtime art

The valley is a panoramic matte on a distant cylinder. The halls, gates, lamps, folding screens, maples, characters, projectiles and floor are rendered 3D geometry. The screen panels meet at hinges and retain their own depth and shadows. Each Heron feather uses a mesh fitted to its alpha silhouette so the depth pass follows the individual plume.

ImageGen produced the following original material plates for this build. The production inputs requested:

| Texture | Art direction |
| --- | --- |
| `karst-valley.jpg` | Panoramic dusk valley with cliff monasteries, layered limestone ridges and cold low clouds. |
| `tide-icon.jpg` | Orthographic worn gold-leaf tide deity with herons and malachite waves. |
| `lacquer-bay.jpg` | Lacquered Ming timber bay, pierced window lattice, amber paper and painted brackets. |
| `heron-silk.jpg` | Paired ivory cranes, metallic thread and reeds on deep blue-green silk. |
| `cinder-mask.jpg` | Horned funerary carving with coiling gilded serpents in charred stone. |
| `dragon-mantle.jpg` | Gold-thread carp-dragon climbing through a broken halo on oxblood damask. |
| `rain-stones.jpg` | Weathered basalt with fine veins, moss and sparse wet leaves. |
| `heron-quill.png` | Isolated ivory flight feather with a dark quill and worn gold detailing. |
| `warden-mask.png` | Frontal patinated bronze ceremonial face with cheek guards and eye slits. |

The release images live under `public/art/`. The runtime bends the mask to the helm, drapes the textiles over shaped meshes and instances the leaves as independent geometry.

## Captures

- [Bellwarden, close engagement](bellwarden.jpg)
- [Bellwarden, after strafing](bellwarden-side.jpg)
- [Veiled Heron, wing spread](heron.jpg)
- [Saint of Cinders, side view](cinder.jpg)
- [Veiled Heron, 1080p gameplay clip](heron-exchange.mp4)

[Frame intervals](frame-intervals.json) are browser animation-frame timings from one six-second sequence per encounter, including keyboard combat inputs. At 1440p the median was 16.7 ms in all three fights. The 95th percentile reached 50 ms in the Bellwarden fight and 100.1 ms in Cinders during this run.
