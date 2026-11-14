# Xingping relief

The local height sample covers part of the Li River valley around Xingping, Guangxi, China. It is cropped from the N24 E110 GLO-30 surface model. Each unsigned little-endian 16-bit value stores tenths of a metre. The crop has 481 columns and 401 rows. The native fitting rotates it, changes the horizontal and vertical scales, and lowers the central area under the playable valley floor.

To regenerate `Xingping.r16.gz`, download the [source COG](https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N24_00_E110_00_DEM/Copernicus_DSM_COG_10_N24_00_E110_00_DEM.tif) and run `python art/extract_river_heights.py tile.tif native/Art/RiverPeaks/Xingping.r16.gz` with Pillow installed. The extractor verifies the tile SHA-256 before cropping.

produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved

The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30.

[Copernicus DEM collection and licensing](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) · [GLO-30 licence](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf) · [AWS Open Data source](https://registry.opendata.aws/copernicus-dem/)

The ground-cover texture contains modified Copernicus Sentinel data 2024. It uses the true-colour and scene-classification products from [S2B_49RDH_20241003_0_L2A](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_49RDH_20241003_0_L2A). The bake retains forest mottling, suppresses roads and settlements, and uses the elevation gradient for exposed limestone. Regenerate with `python art/river_cover.py` using NumPy, rasterio and Pillow. The shipped game reads the local baked textures.
