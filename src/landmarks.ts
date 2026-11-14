import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { moonGatePorch } from "./moon-gate";
import { ArtLibrary } from "./assets";

type Palette = Record<string, T.MeshStandardMaterial>;
const tau = Math.PI * 2;

// Static architecture is batched by material, including reveal faces and trim.
// Keep UVs in metres on masonry so long walls retain their surface detail.
class Masonry {
  private batches = new Map<T.Material, T.BufferGeometry[]>();
  add(
    source: T.BufferGeometry,
    material: T.Material,
    x: number,
    y: number,
    z: number,
    yaw = 0,
  ) {
    const geometry = source.index ? source.toNonIndexed() : source;
    if (geometry !== source) source.dispose();
    geometry.rotateY(yaw).translate(x, y, z);
    let batch = this.batches.get(material);
    if (!batch) this.batches.set(material, (batch = []));
    batch.push(geometry);
  }
  block(
    material: T.Material,
    x: number,
    y: number,
    z: number,
    w: number,
    h: number,
    d: number,
  ) {
    const block = new T.BoxGeometry(w, h, d);
    const { position, normal, uv } = block.attributes;
    for (let i = 0; i < uv.count; i++) {
      const u =
        Math.abs(normal.getX(i)) > 0.5
          ? position.getZ(i) + z
          : position.getX(i) + x;
      const v =
        Math.abs(normal.getY(i)) > 0.5
          ? position.getZ(i) + z
          : position.getY(i) + y;
      uv.setXY(i, u * 0.31, v * 0.31);
    }
    this.add(block, material, x, y, z);
  }
  finish(target: T.Object3D) {
    for (const [material, shapes] of this.batches) {
      const mesh = new T.Mesh(mergeGeometries(shapes), material);
      mesh.castShadow = mesh.receiveShadow = true;
      target.add(mesh);
      shapes.forEach((s) => s.dispose());
    }
  }
}

function slab(outline: T.Shape, depth: number, bevel: number) {
  return new T.ExtrudeGeometry(outline, {
    depth,
    bevelEnabled: true,
    bevelSegments: 2,
    bevelSize: bevel,
    bevelThickness: bevel,
    curveSegments: 36,
  });
}
function archStone(
  inner: number,
  outer: number,
  a: number,
  b: number,
  depth: number,
) {
  const shape = new T.Shape();
  shape.moveTo(inner * Math.cos(a), inner * Math.sin(a));
  shape.absarc(0, 0, inner, a, b, false);
  shape.lineTo(outer * Math.cos(b), outer * Math.sin(b));
  shape.absarc(0, 0, outer, b, a, true);
  shape.closePath();
  return slab(shape, depth, 0.018);
}
function rock(
  art: ArtLibrary,
  group: T.Group,
  x: number,
  z: number,
  height: number,
  yaw: number,
  width = 1,
) {
  const cliff = art.model("rock_face_01", height);
  cliff.position.set(x, -0.65, z);
  cliff.rotation.y = yaw;
  cliff.scale.x = width;
  group.add(cliff);
}

/** Raised garden crossing visible through the moon gate. A skewed span lets the
 * bridge rails slide past the circular opening as the combat camera orbits. */
function moonBridge(stone: Masonry, m: Palette, lantern: T.Material) {
  const origin = new T.Vector3(0.48, 0, -30);
  const yaw = -0.51;
  const place = (g: T.BufferGeometry, mat: T.Material, x=0, y=0, z=0) => {
    g.translate(x, y, z);
    stone.add(g, mat, origin.x, origin.y, origin.z, yaw);
  };
  const deck = (x: number) => 1.34 + 1.12 * Math.cos(Math.PI * x / 14);
  const radius = 2.46, spring = .17;
  const body = new T.Shape();
  body.moveTo(-7, -.15);
  body.lineTo(-radius, -.15);
  body.lineTo(-radius, spring);
  body.absellipse(0, spring, radius, 1.75, Math.PI, 0, true, 0);
  body.lineTo(radius, -.15);
  body.lineTo(7, -.15);
  for (let i=28; i>=0; i--) {
    const x=-7+i*.5;
    body.lineTo(x,deck(x)-.11);
  }
  body.closePath();
  place(slab(body,1.63,.025),m.rock,0,0,-.815);
  for (let i=0;i<19;i++) {
    const a=Math.PI*i/19, b=Math.PI*(i+1)/19;
    const block=archStone(radius,radius+.29,a+.004,b-.004,.13);
    block.scale(1,1.75/radius,1);
    place(block,m.wall,0,spring,.82);
  }
  const rail=(x1:number,y1:number,x2:number,y2:number,z:number,h:number,w:number) => {
    const beam=new T.BoxGeometry(Math.hypot(x2-x1,y2-y1),h,w);
    beam.rotateZ(Math.atan2(y2-y1,x2-x1));
    place(beam,m.rock,(x1+x2)/2,(y1+y2)/2,z);
  };
  for(let i=0;i<28;i++) {
    const x=-7+i*.5;
    const tread=new T.BoxGeometry(.498,.14,2.04);
    tread.rotateZ(Math.atan2(deck(x+.5)-deck(x),.5));
    place(tread,m.rock,x+.25,deck(x+.25)-.05);
  }
  for(const z of [-.87,.87]) {
    for(let i=0;i<=8;i++) {
      const x=-7+i*1.75, y=deck(x);
      place(new T.BoxGeometry(.22,.85,.23),m.wall,x,y+.415,z);
      place(new T.CylinderGeometry(.126,.153,.16,8),m.rock,x,y+.90,z);
      place(new T.SphereGeometry(.146,10,8).scale(.86,1.22,.86),m.rock,x,y+1.04,z);
      if(i===8)continue;
      const end=x+1.75;
      rail(x,y+.71,end,deck(end)+.71,z,.105,.17);
      rail(x,y+.26,end,deck(end)+.26,z,.085,.14);
      for(const f of [.33,.67]) {
        const px=x+1.75*f;
        place(new T.BoxGeometry(.085,.43,.10),m.wall,px,T.MathUtils.lerp(y,deck(end),f)+.48,z);
      }
    }
  }
  const x=2.65, z=-1.02, y=deck(x);
  place(new T.CylinderGeometry(.062,.10,1.32,8),m.wood,x,y+.64,z);
  place(new T.BoxGeometry(.60,.11,.60),m.wood,x,y+1.35,z);
  place(new T.BoxGeometry(.37,.56,.37),lantern,x,y+1.68,z);
  for(const a of [-.2,.2])for(const b of [-.2,.2])
    place(new T.BoxGeometry(.04,.61,.04),m.wood,x+a,y+1.68,z+b);
  place(new T.ConeGeometry(.50,.32,4).rotateY(Math.PI/4),m.roof,x,y+2.11,z);
  place(new T.SphereGeometry(.074,10,8),m.gold,x,y+2.30,z);
}

/** Weathered garden wall with a circular opening cut through its entire thickness. */
export function heronGarden(art: ArtLibrary, m: Palette, rand: () => number) {
  const garden = new T.Group(),
    stone = new Masonry();
  garden.name = "Heron moon garden";
  const lime = new T.MeshStandardMaterial({
    color: 0xbfc5af,
    roughness: 0.93,
    map: art.textures.get("rock-color"),
    normalMap: art.textures.get("rock-normal"),
    normalScale: new T.Vector2(0.18, 0.18),
  });
  const wall = new T.Shape();
  wall.moveTo(-8.3, 0);
  wall.lineTo(8.3, 0);
  wall.lineTo(8.3, 6.45);
  wall.lineTo(-8.3, 6.45);
  wall.closePath();
  const opening = new T.Path();
  opening.absarc(0, 2.96, 2.87, 0, tau, true);
  wall.holes.push(opening);
  stone.add(slab(wall, 0.82, 0.038), lime, 0, 0, -19.5);
  for (let i = 0; i < 44; i++) {
    const a = (tau * i) / 44,
      b = (tau * (i + 1)) / 44;
    stone.add(
      archStone(2.74, 3.12, a + 0.003, b - 0.003, 0.99),
      m.rock,
      0,
      2.96,
      -19.55,
    );
  }
  for (const s of [-1, 1]) {
    stone.block(m.rock, s * 5.7, 0.28, -19.1, 5.1, 0.54, 1.12);
    stone.block(lime, s * 13.1, 1.95, -20.3, 9.6, 3.9, 0.75);
    for (let j = 0; j < 3; j++)
      stone.block(
        m.roof,
        s * 13.1,
        4.02 + j * 0.11,
        -20.3,
        9.85,
        0.12,
        1.2 - j * 0.16,
      );
    // Small lattice windows are raised timber frames set into shadowed recesses.
    for (const xx of [s * 6, s * 11, s * 15]) {
      const cy = Math.abs(xx) === 6 ? 3.6 : 2.2,
        zz = Math.abs(xx) === 6 ? -18.61 : -19.89;
      stone.block(m.dark, xx, cy, zz, 1.65, 1.86, 0.1);
      for (const dx of [-0.86, 0.86])
        stone.block(m.wood, xx + dx, cy, zz + 0.08, 0.13, 2.05, 0.14);
      for (const dy of [-0.96, 0.96])
        stone.block(m.wood, xx, cy + dy, zz + 0.08, 1.82, 0.12, 0.14);
      for (let j = 0; j < 7; j++) {
        const strip = new T.BoxGeometry(0.045, 1.18, 0.07);
        strip.rotateZ(j % 2 ? -0.78 : 0.78);
        stone.add(
          strip,
          m.wood,
          xx - 0.57 + (j >> 1) * 0.36,
          cy + (j % 2 ? -0.26 : 0.26),
          zz + 0.1,
        );
      }
    }
  }
  const ceramic = new T.MeshPhysicalMaterial({
    color: 0x506e68, roughness: 0.44, clearcoat: 0.46, clearcoatRoughness: 0.31,
    bumpMap: art.textures.get("rock-rough"), bumpScale: 0.012,
  });
  const timber = new T.MeshStandardMaterial({
    map: art.textures.get("wood-color"), color: 0x994832, roughness: 0.61,
  });
  const lampPaper = new T.MeshStandardMaterial({
    color: 0xf2bc83, emissive: 0xff8f42, emissiveIntensity: 1.28, roughness: 0.89,
  });
  const porch = moonGatePorch({timber, ceramic, bronze:m.gold, stone:m.rock, paper:lampPaper});
  porch.position.z = -19.09;
  garden.add(porch);
  const paper = new T.MeshStandardMaterial({
    color: 0xddcba3, emissive: 0xffbb68, emissiveIntensity: .85, roughness: .88,
  });
  moonBridge(stone, m, paper);
  stone.finish(garden);
  rock(art, garden, -8.4, -21, 6.8, 0.55, 1.05);
  rock(art, garden, 10.4, -23, 8.6, -0.62);
  rock(art, garden, -4.8, -38, 13, 0.4);
  rock(art, garden, 10, -46, 16, -0.54);
  // Slender jointed culms with branching, two-sided lanceolate leaf sprays.
  const grove = new Masonry(),
    leaves: number[] = [],
    colors: number[] = [];
  const stem = new T.MeshStandardMaterial({ color: 0x566247, roughness: 0.73 });
  const joint = new T.MeshStandardMaterial({
    color: 0x889076,
    roughness: 0.85,
  });
  for (let clump = 0; clump < 16; clump++) {
    const side = clump % 2 ? 1 : -1,
      cx = side * (6 + rand() * 15),
      cz = -19 - rand() * 15;
    for (let reed = 0; reed < 5; reed++) {
      const x = cx + rand() * 2,
        z = cz + rand() * 2,
        height = 5 + rand() * 7,
        lean = (rand() - 0.5) * 0.28;
      for (let k = 0; k < 8; k++) {
        const h = height / 8,
          y = h * (k + 0.5),
          r = 0.052 * (1 - k * 0.052);
        const shaft = new T.CylinderGeometry(r * 0.94, r, h * 1.025, 6);
        shaft.rotateZ(lean);
        const xx = x - y * Math.sin(lean),
          yy = y * Math.cos(lean);
        grove.add(shaft, stem, xx, yy, z);
        grove.add(
          new T.CylinderGeometry(r * 1.22, r * 1.2, 0.056, 7),
          joint,
          x - (y + h * 0.5) * Math.sin(lean),
          (y + h * 0.5) * Math.cos(lean),
          z,
        );
        if (k < 3) continue;
        const dir = rand() * tau,
          length = 0.6 + rand() * 1.05;
        const branch = new T.Vector3(
          Math.cos(dir) * length,
          0.35 + rand() * 0.45,
          Math.sin(dir) * length,
        );
        const twig = new T.CylinderGeometry(0.01, 0.026, branch.length(), 5);
        twig.applyQuaternion(
          new T.Quaternion().setFromUnitVectors(
            new T.Vector3(0, 1, 0),
            branch.clone().normalize(),
          ),
        );
        grove.add(
          twig,
          stem,
          xx + branch.x / 2,
          yy + branch.y / 2,
          z + branch.z / 2,
        );
        for (let n = 0; n < 9; n++) {
          const t = 0.2 + n * 0.09,
            a = dir + (n % 2 ? 1 : -1) * (0.58 + rand() * 0.6),
            l = 0.31 + rand() * 0.36;
          const bx = xx + branch.x * t,
            by = yy + branch.y * t,
            bz = z + branch.z * t;
          const tip = [
            bx + Math.cos(a) * l,
            by - 0.12 - rand() * 0.19,
            bz + Math.sin(a) * l,
          ];
          const mx = (bx + tip[0]) * 0.5,
            mz = (bz + tip[2]) * 0.5,
            dx = Math.sin(a) * 0.056,
            dz = -Math.cos(a) * 0.056;
          const base = [bx, by, bz],
            left = [mx + dx, by + 0.025, mz + dz],
            right = [mx - dx, by + 0.014, mz - dz];
          leaves.push(...base, ...left, ...tip, ...base, ...tip, ...right);
          const shade = 0.48 + rand() * 0.43;
          for (let v = 0; v < 6; v++)
            colors.push(shade * 0.42, shade * 0.55, shade * 0.32);
        }
      }
    }
  }
  grove.finish(garden);
  const foliage = new T.BufferGeometry();
  foliage.setAttribute("position", new T.Float32BufferAttribute(leaves, 3));
  foliage.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
  foliage.computeVertexNormals();
  garden.add(
    new T.Mesh(
      foliage,
      new T.MeshStandardMaterial({
        side: T.DoubleSide,
        vertexColors: true,
        roughness: 0.88,
      }),
    ),
  );
  return garden;
}

/** Rock-cut burial court with a recessed arch, flanking votive niches and a suspended bronze lamp. */
export function cinderReliquary(art: ArtLibrary, m: Palette) {
  const shrine = new T.Group(),
    masonry = new Masonry();
  shrine.name = "Cinder cliff reliquary";
  for (const s of [-1, 1]) {
    rock(art, shrine, s * 9.7, -23, 12.6, s * -0.48, 1.24);
    rock(art, shrine, s * 17, -18, 10.8, s * -0.85, 1.12);
    rock(art, shrine, s * 15, -32, 18.8, s * -0.51, 1.16);
    masonry.block(m.rock, s * 5.1, 2.12, -20.8, 1.42, 4.24, 2.36);
    for (let i = 0; i < 7; i++)
      masonry.block(m.roof, s * 5.1, 0.4 + i * 0.62, -19.65, 1.58, 0.12, 0.35);
    for (let col = 0; col < 4; col++)
      for (let row = 0; row < 3; row++) {
        const x = s * (6.2 + col * 1.12),
          y = 1.18 + row * 1.34,
          z = -18.44 - col * 0.12;
        masonry.block(m.dark, x, y, z, 0.91, 1.02, 0.14);
        masonry.block(m.rock, x, y - 0.52, z + 0.11, 1.02, 0.15, 0.57);
        for (const sign of [-1, 1])
          masonry.block(m.rock, x + sign * 0.48, y, z + 0.06, 0.13, 1.15, 0.36);
        masonry.add(
          archStone(0.37, 0.55, 0, Math.PI, 0.3),
          m.rock,
          x,
          y + 0.44,
          z - 0.01,
        );
        masonry.add(
          new T.CylinderGeometry(0.18, 0.085, 0.15, 12),
          m.gold,
          x,
          y - 0.36,
          z + 0.38,
        );
        masonry.add(
          new T.SphereGeometry(0.066, 9, 7).scale(0.78, 1.6, 0.8),
          m.fire,
          x,
          y - 0.22,
          z + 0.38,
        );
      }
  }
  for (let i = 0; i < 27; i++)
    masonry.add(
      archStone(
        4.39,
        5.79,
        (Math.PI * i) / 27 + 0.002,
        (Math.PI * (i + 1)) / 27 - 0.002,
        2.5,
      ),
      m.rock,
      0,
      4.14,
      -22.1,
    );
  for (let i = 0; i < 25; i++)
    masonry.add(
      archStone(
        4.42,
        4.64,
        (Math.PI * i) / 25 + 0.003,
        (Math.PI * (i + 1)) / 25 - 0.003,
        0.28,
      ),
      m.gold,
      0,
      4.14,
      -19.75,
    );
  for (let i = 0; i < 4; i++)
    masonry.block(
      m.rock,
      0,
      0.12 + i * 0.21,
      -17.7 - i * 0.67,
      9.2 - i * 0.32,
      0.24 + i * 0.42,
      1,
    );
  masonry.block(m.dark, 0, 4, -27, 12, 8.3, 1.2);
  rock(art, shrine, -2.4, -33, 13.0, 0.43, 1.24);
  const lamp = art.model("chinese_chandelier", 3.7);
  lamp.position.set(0, 2.65, -22.6);
  shrine.add(lamp);
  masonry.add(
    new T.CylinderGeometry(0.028, 0.028, 3.4, 9),
    m.gold,
    0,
    8,
    -22.6,
  );
  masonry.finish(shrine);
  const glow = new T.PointLight(0xff9345, 115, 13, 2);
  glow.position.set(0.8, 4, -19.5);
  shrine.add(glow);
  return shrine;
}
