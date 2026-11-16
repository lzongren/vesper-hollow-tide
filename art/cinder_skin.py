"""Repaint the existing CC0 sorcerer rig in its own UVs. Requires NumPy and Pillow."""
import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image
from cinder_gesture import add_gestures

ROOT = Path(__file__).resolve().parents[1] / "public/models"


def read_accessor(doc, data, index):
    acc = doc["accessors"][index]
    view = doc["bufferViews"][acc["bufferView"]]
    offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    channels = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    dtype = {5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[acc["componentType"]]
    return np.frombuffer(data, dtype=dtype, count=acc["count"] * channels, offset=offset).reshape(-1, channels)


def rasterize(doc, data, size):
    prim = doc["meshes"][0]["primitives"][0]
    attributes = prim["attributes"]
    pos = read_accessor(doc, data, attributes["POSITION"]) * 1.85
    uv = read_accessor(doc, data, attributes["TEXCOORD_0"]) * size - 0.5
    indices = read_accessor(doc, data, prim["indices"]).reshape(-1, 3)
    normal = read_accessor(doc, data, attributes["NORMAL"])
    joints = read_accessor(doc, data, attributes["JOINTS_0"])
    weights = read_accessor(doc, data, attributes["WEIGHTS_0"])
    names = [doc["nodes"][i]["name"] for i in doc["skins"][0]["joints"]]
    limb = np.array([n.endswith(("Hand", "Arm")) for n in names])[joints]
    joint_weight = (limb * weights).sum(axis=1)
    # Position, surface normal and bone influence are interpolated per texel.
    attributes = np.column_stack([pos, normal, joint_weight])
    atlas = np.zeros((size, size, attributes.shape[1]), dtype=np.float32)
    valid = np.zeros((size, size), bool)
    for tri in indices:
        a, b, c = uv[tri]
        e, f = b-a, c-a
        det = e[0]*f[1] - e[1]*f[0]
        if abs(det) < 1e-5:
            continue
        lo = np.maximum(0, np.ceil(np.minimum(np.minimum(a,b),c)).astype(int))
        hi = np.minimum(size-1, np.floor(np.maximum(np.maximum(a,b),c)).astype(int))
        if (lo > hi).any():
            continue
        sl = np.s_[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        dx = np.arange(lo[0],hi[0]+1)[None,:] - a[0]
        dy = np.arange(lo[1],hi[1]+1)[:,None] - a[1]
        u = (dx*f[1] - dy*f[0])/det
        v = (dy*e[0] - dx*e[1])/det
        inside = (u>=0) & (v>=0) & (u+v<=1)
        a0, a1, a2 = attributes[tri]
        atlas[sl][inside] = a0 + u[inside,None]*(a1-a0) + v[inside,None]*(a2-a0)
        valid[sl] |= inside
    # Pad the UV islands so filtering and tangent-space gradients stay local.
    for _ in range(5):
        available = valid.copy()
        for axis, step in ((0,1),(0,-1),(1,1),(1,-1)):
            src = np.roll(available, step, axis=axis)
            empty = src & ~valid
            atlas[empty] = np.roll(atlas,step,axis=axis)[empty]
            valid |= empty
    return atlas, valid


def jpeg(array):
    output = io.BytesIO()
    Image.fromarray(np.uint8(np.clip(array,0,255))).save(output,format="JPEG",quality=92,subsampling=0)
    return output.getvalue()


def mix(a, b, weight):
    return a + (b-a)*weight[...,None]


def bake():
    glb = (ROOT/"sorcerer.glb").read_bytes()
    n = struct.unpack_from("<I",glb,12)[0]
    doc = json.loads(glb[20:20+n])
    data = bytearray(glb[28+n:])
    view = doc["bufferViews"][doc["images"][0]["bufferView"]]
    original = Image.open(io.BytesIO(data[view["byteOffset"]:view["byteOffset"]+view["byteLength"]]))
    size = 1536
    base = np.asarray(original.resize((size,size),Image.Resampling.LANCZOS),dtype=np.float32)
    atlas, valid = rasterize(doc,data,size)
    x,y,z,nx,ny,nz,weight = atlas.transpose(2,0,1)
    x = abs(x)
    coverage = np.clip(weight*2.1-.10,0,1) * valid
    # Old fire tips guide the shape of the horn sheath; its highlight now
    # comes from the court lights. The narrow bed at its base retains heat.
    r,g,b = base.transpose(2,0,1)
    keratin = np.clip((r-np.maximum(g,b)-8)/71,0,1) * np.clip((r-45)/80,0,1)
    axis = x*.76 + z*.65 + .11*y
    fold = np.sin(82*axis + 4.2*np.sin(10*y+3*z) + 1.8*np.sin(14*x-6*y))
    ridge = np.exp(-((fold+.55)/.21)**2)
    crease = np.clip(1-abs(np.sin(48*y+8*z+2.1*np.sin(9*x+4*z)))*3.5,0,1)
    fleck = np.sin(93*x+147*y+81*z)*np.cos(151*x-83*z)
    value = (r*.27 + g*.56 + b*.17)/255
    ash = np.stack([103+48*value,93+42*value,82+39*value],axis=-1)
    ash += (11*fold-23*ridge-16*crease+5*fleck)[...,None]
    tip = np.clip((r+g*.75-85)/215,0,1)
    horn = mix(np.array([62,42,32]),np.array([229,206,162]),tip)
    horn += (9*np.sin(180*z + 52*x + 24*y) + 6*fleck)[...,None]
    skin = mix(ash,horn,keratin)
    color = mix(base,skin,coverage)
    vein = np.clip(1-abs(keratin-.35)/.15,0,1)*np.clip((r-88)/110,0,1)
    # All former emissive pigment outside the limbs is strongly attenuated.
    emission = mix(base*.72,np.stack([vein*157, vein*54, vein*12],axis=-1),coverage)
    rough = np.clip(.78-.32*coverage*keratin+.08*coverage*crease,.34,.92)
    surface = np.stack([np.ones_like(rough),rough,np.zeros_like(rough)],axis=-1)
    height = coverage*(.28*fold-.55*ridge-.33*crease+.07*fleck)*(1-.8*keratin)
    dy,dx = np.gradient(height)
    nm = np.stack([-dx,dy,np.ones_like(dx)],axis=-1)
    nm /= np.linalg.norm(nm,axis=-1,keepdims=True)
    material = doc["materials"][0]
    material["name"] = "Cinder ascetic"
    for label, pixels, slot in [
        ("Ash and horn",color,"color"),("Cinders under the nail",emission,"emission"),
        ("Creased hide",127.5*(1+nm),"normal"),("Skin and keratin finish",255*surface,"roughness")
    ]:
        encoded = jpeg(pixels)
        data.extend(bytes((-len(data))%4))
        index=len(doc["bufferViews"])
        doc["bufferViews"].append({"buffer":0,"byteOffset":len(data),"byteLength":len(encoded)})
        data.extend(encoded)
        source=len(doc["images"])
        doc["images"].append({"bufferView":index,"mimeType":"image/jpeg","name":label})
        idx=len(doc["textures"]);doc["textures"].append({"sampler":0,"source":source})
        tex={"index":idx}
        if slot=="color":material["pbrMetallicRoughness"]["baseColorTexture"]=tex
        elif slot=="roughness":material["pbrMetallicRoughness"]["metallicRoughnessTexture"]=tex
        elif slot=="normal":material["normalTexture"]=tex
        else:material["emissiveTexture"]=tex
    material["pbrMetallicRoughness"].update(roughnessFactor=1,metallicFactor=0)
    material["extensions"]["KHR_materials_specular"]={"specularFactor":.65}
    primitive=doc["meshes"][0]["primitives"][0]
    attr=primitive["attributes"]
    add_gestures(doc, data, primitive,
                 read_accessor(doc,data,attr["POSITION"]).copy(), read_accessor(doc,data,attr["NORMAL"]).copy(),
                 read_accessor(doc,data,primitive["indices"]).reshape(-1,3).copy())
    data.extend(bytes((-len(data))%4))
    doc["buffers"][0]["byteLength"]=len(data)
    payload=json.dumps(doc,separators=(",",":")).encode()
    payload+=b" "*((-len(payload))%4)
    (ROOT/"cinder-ascetic.glb").write_bytes(struct.pack("<4sIIII",b"glTF",2,28+len(payload)+len(data),len(payload),0x4E4F534A)+payload+struct.pack("<I4s",len(data),b"BIN\0")+data)


if __name__ == "__main__":
    bake()
