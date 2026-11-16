"""Set the limestone spur and its rooted summit trees beyond the northern quay."""

from bind_pilgrim import Glb
from lotus_beds import pond_mesh
from river_relief import grove_geometry, summit_forest


def open_pond(vertices):
    # Each authored summit starts with a closed ring at the common foot level.
    # Translate the whole connected spur, including its normals and UV layout.
    bottom = min(v[1] for v in vertices)
    foot = [abs(v[1] - bottom) < 0.0001 for v in vertices]
    starts = [i for i, on in enumerate(foot) if on and (i == 0 or not foot[i - 1])]
    if len(starts) != 8:
        raise ValueError("Expected eight shrine spurs")
    shift = None
    for lo, hi in zip(starts, starts[1:] + [len(vertices)]):
        ring = []
        for i in range(lo, hi):
            if not foot[i]:
                break
            ring.append(vertices[i])
        cx = sum(v[0] for v in ring) / len(ring)
        cz = sum(v[2] for v in ring) / len(ring)
        if abs(cx + 46) < 1 and abs(cz - 14) < 1:
            shift = (lo, hi)
    if shift is None:
        raise ValueError("Cannot identify the spur above the pond")
    lo, hi = shift
    return (
        list(vertices[:lo])
        + [(x - 7, h, z + 38) for x, h, z in vertices[lo:hi]]
        + list(vertices[hi:])
    )


def escarpment(source, dest):
    rock = Glb(source.parent / "Art" / "ShrineCliffWalk.glb")
    node = next(n for n in rock.doc["nodes"] if n.get("name") == "Limestone spurs")
    original = rock.doc["meshes"][node["mesh"]]["primitives"][0]
    out = pond_mesh(source, "MoonEscarpment")
    slot = out.material("MountainFace", None, None, (0.3, 0.31, 0.28), 0.9)
    attrs = {}
    for key, acc in original["attributes"].items():
        data = rock.values(acc)
        if key == "POSITION":
            data = open_pond(data)
        fmt = rock.doc["accessors"][acc]["type"]
        attrs[key] = out.glb.data(data, fmt, bounds=key == "POSITION")
    indices = out.glb.data(rock.values(original["indices"]), "SCALAR", 5125)
    out.glb.doc["meshes"][0]["primitives"] = [
        dict(attributes=attrs, indices=indices, material=slot)
    ]
    out.glb.save(dest)


def grove(source, dest):
    art = source.parent / "Art"
    out = pond_mesh(source, "MoonSummitPines")
    slot = out.material("SummitNeedles", None, None, (1, 1, 1), 0.9)
    cover = out.glb.image(
        (art / "RiverPeaks/ConiferViews.png").read_bytes(),
        "image/png",
        "GardenSummitConifers",
    )
    mat = out.glb.doc["materials"][slot]
    mat.update(alphaMode="MASK", alphaCutoff=0.30)
    mat["pbrMetallicRoughness"]["baseColorTexture"] = cover
    pts, normals, indices, uv, _ = grove_geometry(
        summit_forest(art / "ShrineCliffWalk.glb", reshape=open_pond)
    )
    attrs = dict(
        POSITION=out.glb.data(pts, "VEC3", bounds=True),
        NORMAL=out.glb.data(normals, "VEC3"),
        TEXCOORD_0=out.glb.data(uv, "VEC2"),
    )
    out.glb.doc["meshes"][0]["primitives"] = [
        dict(
            attributes=attrs,
            indices=out.glb.data([(i,) for i in indices], "SCALAR", 5125),
            material=slot,
        )
    ]
    out.glb.save(dest)
