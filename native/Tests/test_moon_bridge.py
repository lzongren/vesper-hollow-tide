from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
from moon_bridge import deck
from moon_escarpment import open_pond
from lotus_beds import planting
from bind_pilgrim import Glb


class BridgeDeckTest(unittest.TestCase):
    def test_treads_rise_symmetrically_to_the_landing(self):
        heights = [deck(-14 + (i + 0.5) * 28 / 96) for i in range(96)]
        self.assertEqual(heights, list(reversed(heights)))
        self.assertEqual(heights[:48], sorted(heights[:48]))
        self.assertAlmostEqual(heights[0], 0.10)
        self.assertAlmostEqual(heights[47], 4.00)
        self.assertLessEqual(
            max(abs(b - a) for a, b in zip(heights, heights[1:])), 0.261
        )

    def test_lotus_colonies_include_flower_and_leaf_surfaces(self):
        native = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "LotusColony.glb"
            planting(native / "SourceAssets", path)
            glb = Glb(path)
            slots = {
                glb.doc["materials"][p["material"]]["name"]: p
                for p in glb.doc["meshes"][0]["primitives"]
            }
            self.assertTrue(
                {"LotusReceptacle", "LotusIvory", "PondStems"} <= slots.keys()
            )
            for i in range(4):
                leaf = slots["LotusLeaf" + str(i)]
                tex = glb.values(leaf["attributes"]["TEXCOORD_0"])
                self.assertGreater(
                    max(uv[0] for uv in tex) - min(uv[0] for uv in tex), 0.94
                )

    def test_spur_is_translated_whole_without_stretching_its_faces(self):
        rock = Glb(Path(__file__).resolve().parents[1] / "Art/ShrineCliffWalk.glb")
        node = next(n for n in rock.doc["nodes"] if n.get("name") == "Limestone spurs")
        primitive = rock.doc["meshes"][node["mesh"]]["primitives"][0]
        positions = rock.values(primitive["attributes"]["POSITION"])
        result = open_pond(positions)
        shifts = [
            (round(x - a, 5), round(y - b, 5), round(z - c, 5))
            for (a, b, c), (x, y, z) in zip(positions, result)
        ]
        self.assertEqual(set(shifts), {(0, 0, 0), (-7, 0, 38)})
        indices = rock.values(primitive["indices"])
        for i in range(0, len(indices), 3):
            self.assertEqual(len({shifts[j] for (j,) in indices[i : i + 3]}), 1)
