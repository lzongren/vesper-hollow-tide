"""Build the Drowned Belfry's original bronze bell. Requires numpy and Pillow."""
import io
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

TAU = np.pi * 2
ROOT = Path(__file__).resolve().parents[1]


def grain(size, width, height, rng):
    """Periodic smooth noise, including across the back of the casting."""
    lattice = rng.normal(size=(height, width))
    x = np.arange(size) * width / size
    y = np.arange(size) * height / size
    col, row = x.astype(int), y.astype(int)
    fx, fy = x % 1, (y % 1)[:, None]
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    top = lattice[row[:, None], col] * (1 - fx) + lattice[row[:, None], (col + 1) % width] * fx
    bottom = lattice[(row[:, None] + 1) % height, col] * (1 - fx) + lattice[(row[:, None] + 1) % height, (col + 1) % width] * fx
    return top * (1 - fy) + bottom * fy


def emboss(u, v):
    """Rows of overlapping lotus leaves and an interlocking cloud-scroll frieze."""
    def line(distance, width):
        return np.exp(-np.square(distance / width))

    def petal(count, start, height, offset):
        lateral = abs((u * count + offset) % 1 - 0.5) * 2
        tip = start + height * (1 - lateral ** 1.65)
        return line(v - tip, .012) + .42 * line(v - tip + .035, .009)

    scroll = np.cos(TAU * 12 * u)
    bands = sum(line(v - center, width) for center, width in
                ((.055,.012),(.092,.007),(.31,.012),(.34,.007),(.65,.012),(.68,.007),(.86,.012)))
    return (.40 * bands + .32 * petal(16, .11, .16, 0) + .19 * petal(16, .14, .07, .5)
            + .34 * line(v - (.493 + .105 * scroll), .014)
            + .29 * line(v - (.493 - .105 * scroll), .014)
            + .45 * line(v - (.73 + .075 * abs(np.sin(TAU * 8 * u))), .012))


def maps(size=1024):
    rng = np.random.default_rng(78413)
    axis = (np.arange(size) + .5) / size
    u, v = axis[None, :], (1 - axis)[:, None]
    relief = emboss(u, v)
    coarse = grain(size, 21, 11, rng)
    streaks = grain(size, 108, 17, rng)
    pits = grain(size, 236, 186, rng)
    fine = rng.normal(0, 1, (size, size))
    patina = np.clip(.32 + .31 * coarse + .20 * streaks + .11 * pits - .46 * relief, 0, 1)
    wear = np.clip(.14 + relief * 1.1 + .12 * coarse, 0, 1)
    copper = np.array([118, 76, 46]) + wear[..., None] * np.array([81, 74, 49])
    oxide = np.array([43, 90, 79]) + pits[..., None] * 5
    color = copper * (1 - patina[..., None]) + oxide * patina[..., None]
    color += (3 * fine + 5 * pits)[..., None]
    roughness = np.clip(.49 + .38 * patina - .20 * wear + .045 * pits, .2, .96)
    metalness = np.clip(.94 - .66 * patina, .18, .98)
    orm = np.stack((np.clip(.86 + relief * .18, 0, 1), roughness, metalness), axis=-1)
    height = relief * 1.2 + .06 * pits + .025 * fine
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * -3
    dy = np.gradient(height, axis=0) * 2
    normal = np.stack((dx, dy, np.ones_like(height)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    def jpg(values):
        out = io.BytesIO()
        Image.fromarray(np.clip(values, 0, 255).astype('uint8')).save(out, format='JPEG', quality=90, subsampling=0)
        return out.getvalue()
    return [jpg(color), jpg(orm * 255), jpg((normal * .5 + .5) * 255)]


def geometry():
    vertices, coords, faces = [], [], []
    def grid(points, uv, flip=False):
        rows, cols, _ = points.shape
        offset = sum(len(v) for v in vertices)
        vertices.append(points.reshape(-1, 3))
        coords.append(uv.reshape(-1, 2))
        a = (np.arange(rows - 1)[:, None] * cols + np.arange(cols - 1) + offset).ravel()
        triangles = np.stack((a, a + cols, a + 1, a + 1, a + cols, a + cols + 1), axis=-1).reshape(-1, 3)
        faces.append(triangles[:, ::-1] if flip else triangles)

    def spun(y, radius, u, v, scallop=0):
        angle = u * TAU
        return np.stack((radius * np.cos(angle), y + scallop * np.cos(angle * 8), radius * np.sin(angle)), axis=-1)

    u, v = np.meshgrid(np.linspace(0, 1, 193), np.linspace(0, 1, 97))
    profile_y = [0,.024,.055,.095,.14,.32,.58,.78,.89,.96,1]
    profile_r = [.988,1,.992,.955,.89,.765,.696,.665,.635,.47,.20]
    radius = np.interp(v, profile_y, profile_r) + .015 * emboss(u, v)
    mouth = .053 * (1-v) ** 4
    grid(spun(v*1.48, radius,u,v,mouth),np.stack((u,1-v),axis=-1))
    # Turn the lip inward, then rise to the enclosed inner vault.
    ui, row = np.meshgrid(u[0],np.arange(7))
    ri = np.take([.988,.968,.917,.77,.59,.46,.001],row)
    yi = np.take([0.,-.021,-.006,.29,.91,1.35,1.39],row)
    grid(spun(yi,ri,ui,row,.053*np.exp(-yi*4)),np.stack((ui,.985-.045*row),axis=-1))
    # A cast arch emerges from the crown. The narrow clapper hangs inside the mouth.
    a,b=np.meshgrid(np.linspace(0,TAU,81),np.linspace(0,TAU,17))
    channel=.063*(1+.09*np.cos(a*16))
    grid(np.stack(((.265+channel*np.cos(b))*np.cos(a),1.55+(.256+channel*np.cos(b))*np.sin(a),channel*np.sin(b)),axis=-1),
         np.stack((a/TAU,.075+.05*b/TAU),axis=-1), flip=True)
    uc, rows=np.meshgrid(u[0],np.arange(8))
    bodyr=np.take([.001,.075,.12,.13,.08,.039,.039,.001],rows)
    bodyy=np.take([-.15,-.13,-.07,.025,.095,.14,1.40,1.42],rows)
    grid(spun(bodyy,bodyr,uc,rows),np.stack((uc,.60+.004*rows),axis=-1))
    cap_u,rr=np.meshgrid(u[0],[.20,.001])
    grid(spun(np.ones_like(rr)*1.48,rr,cap_u,rr),np.stack((cap_u,np.zeros_like(rr)),axis=-1))
    pos=np.concatenate(vertices).astype('<f4')
    idx=np.concatenate(faces).astype('<u2')
    normals=np.zeros_like(pos)
    tri=np.cross(pos[idx[:,1]]-pos[idx[:,0]],pos[idx[:,2]]-pos[idx[:,0]])
    for side in range(3):
        np.add.at(normals,idx[:,side],tri)
    # Average matching vertices at UV seams so the cast surface lights continuously.
    _,group=np.unique(np.round(pos,5),axis=0,return_inverse=True)
    smooth=np.zeros((group.max()+1,3),dtype='<f4')
    np.add.at(smooth,group,normals)
    normals=smooth[group]
    normals/=np.maximum(1e-12,np.linalg.norm(normals,axis=1,keepdims=True))
    return pos,normals,np.concatenate(coords).astype('<f4'),idx


def build():
    pos,norm,uv,faces=geometry()
    payload=bytearray()
    views=[]
    def append(data):
        offset=len(payload)
        payload.extend(data)
        views.append(dict(buffer=0,byteOffset=offset,byteLength=len(data)))
        payload.extend(b'\0'*(-len(payload)%4))
        return len(views)-1
    accessors=[]
    for arr,shape,ctype in [(pos,'VEC3',5126),(norm,'VEC3',5126),(uv,'VEC2',5126),(faces.ravel(),'SCALAR',5123)]:
        accessors.append(dict(bufferView=append(arr.tobytes()),componentType=ctype,count=len(arr),type=shape))
    accessors[0].update(min=pos.min(axis=0).tolist(),max=pos.max(axis=0).tolist())
    images=[dict(bufferView=append(data),mimeType='image/jpeg') for data in maps()]
    doc=dict(asset=dict(version='2.0',generator='Vesper cast bell'),scene=0,scenes=[dict(nodes=[0])],
             nodes=[dict(name='Tide Bell',mesh=0)],meshes=[dict(primitives=[dict(attributes=dict(POSITION=0,NORMAL=1,TEXCOORD_0=2),indices=3,material=0)])],
             buffers=[dict(byteLength=len(payload))],bufferViews=views,accessors=accessors,images=images,
             textures=[dict(source=i) for i in range(3)],materials=[dict(name='Salt-worn cast bronze',
             pbrMetallicRoughness=dict(baseColorTexture=dict(index=0),metallicRoughnessTexture=dict(index=1)),
             normalTexture=dict(index=2,scale=.85),occlusionTexture=dict(index=1))])
    meta=json.dumps(doc,separators=(',',':')).encode()
    meta+=b' '*(-len(meta)%4)
    out=ROOT/'public/models/tide-bell.glb'
    out.write_bytes(struct.pack('<4sIIII',b'glTF',2,28+len(meta)+len(payload),len(meta),0x4E4F534A)+meta+struct.pack('<II',len(payload),0x004E4942)+payload)
    print(f'{out.name}: {len(faces)} triangles, {out.stat().st_size:,} bytes')


if __name__=='__main__':
    build()
