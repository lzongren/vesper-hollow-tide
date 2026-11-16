# Xingping relief

The local height sample covers part of the Li River valley around Xingping, Guangxi, China. It is cropped from the N24 E110 GLO-30 surface model. Each unsigned little-endian 16-bit value stores tenths of a metre. The crop has 481 columns and 401 rows. The native fitting rotates it, changes the horizontal and vertical scales, and lowers the central area under the playable valley floor.

To regenerate `Xingping.r16.gz`, download the [source COG](https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N24_00_E110_00_DEM/Copernicus_DSM_COG_10_N24_00_E110_00_DEM.tif) and run `python art/extract_river_heights.py tile.tif native/Art/RiverPeaks/Xingping.r16.gz` with Pillow installed. The extractor verifies the tile SHA-256 before cropping.

produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved

The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30.

[Copernicus DEM collection and licensing](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) · [GLO-30 licence](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf) · [AWS Open Data source](https://registry.opendata.aws/copernicus-dem/)

The ground-cover texture contains modified Copernicus Sentinel data 2024. It uses the true-colour and scene-classification products from [S2B_49RDH_20241003_0_L2A](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_49RDH_20241003_0_L2A). The bake retains forest mottling, suppresses roads and settlements, and uses the elevation gradient for exposed limestone. Regenerate with `python art/river_cover.py` using NumPy, rasterio and Pillow. The shipped game reads the local baked textures.

## Conifers and exposed rock

The colour and opacity atlas contains two views each of the first two variants of [Pine Tree 01](https://polyhaven.com/a/pine_tree_01) and [Fir Tree 01](https://polyhaven.com/a/fir_tree_01). Both source models are CC0. Each view is rendered from the source triangles with the corresponding branch mask. The four columns select trees, and the rows are perpendicular views. The game ships the 2048 × 1024 baked atlas.

To rebake on Linux with EGL, install moderngl, NumPy, Pillow and SciPy. Download each model's 1K glTF, its external buffer and diffuse textures with their original relative paths. Put the separate 1K twig alpha JPEG beside the glTF as `twig-alpha.jpg`. Place each bundle under its Poly Haven asset ID in a local directory outside OneDrive. Run `python art/ridge_tree_atlas.py SOURCE_DIRECTORY native/Art/RiverPeaks/ConiferViews.png`.

[Cliff Side](https://polyhaven.com/a/cliff_side) is a CC0 scan by Dario Barresi, James Ray Cock and Jenelle van Heerden. The shader blends its regraded layers with the shrine's existing mineral atlas and the valley's mapped ground cover. To rebake, use the original 2K diffuse and AO JPEGs with `python art/escarpment_stone.py DIFFUSE.jpg AO.jpg native/Art/RiverPeaks/EscarpmentStone.jpg`. The script checks both source digests. [In-game comparisons](../../../docs/runtime/hillside-forest/)
