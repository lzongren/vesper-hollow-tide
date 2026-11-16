import * as T from "three";
import { MarchingCubes } from "three/addons/objects/MarchingCubes.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

const tau = Math.PI * 2;
const startAngle = 0.29,
  endAngle = 1.91;

function shore(t: number, side: number) {
  const angle = T.MathUtils.lerp(startAngle, endAngle, t);
  const width = Math.sin(Math.PI * t) ** 0.6;
  return {
    angle,
    inner: 13.8 + 0.29 * Math.cos(5 * angle + side),
    outer: 14.1 + width * (3.67 + 0.42 * Math.sin(8 * angle + side)),
  };
}

function basinPoint(t: number, depth: number, side: number, y: number) {
  const { angle, inner, outer } = shore(t, side);
  const r = T.MathUtils.lerp(inner, outer, depth);
  return new T.Vector3(side * Math.sin(angle) * r, y, -Math.cos(angle) * r);
}

/** A scholar's rock with water-worn openings through the body. Its ridges,
 * projecting crown and undercut foot share a continuous limestone surface. */
function piercedStone(phase: number, material: T.Material) {
  const cells = 46;
  const iso = new MarchingCubes(cells, material, false, false, 16000);
  iso.isolation = 0;
  const lobes = [
    [-0.18, -0.57, 0, 0.55, 0.34, 0.37],
    [0.12, -0.23, 0, 0.45, 0.53, 0.35],
    [-0.12, 0.16, 0.02, 0.51, 0.48, 0.3],
    [0.12, 0.46, -0.05, 0.35, 0.32, 0.26],
    [0.37, 0.59, -0.04, 0.31, 0.21, 0.22],
    [-0.28, 0.48, 0.05, 0.15, 0.3, 0.17],
    [-0.48, -0.13, -0.05, 0.18, 0.36, 0.25],
  ];
  for (let z = 0; z < cells; z++)
    for (let y = 0; y < cells; y++)
      for (let x = 0; x < cells; x++) {
        const px = (2 * x) / cells - 1,
          py = (2 * y) / cells - 1,
          pz = (2 * z) / cells - 1;
        const u =
          px +
          0.074 * Math.sin(8 * py + phase) +
          0.038 * Math.cos(9 * pz - 4 * py);
        const v = py + 0.036 * Math.cos(7 * px + phase);
        let body = -8;
        for (const [cx, cy, cz, rx, ry, rz] of lobes) {
          const f =
            1 - Math.hypot((u - cx) / rx, (v - cy) / ry, (pz - cz) / rz);
          const blend = Math.max(0, 0.26 - Math.abs(f - body));
          body = Math.max(f, body) + (blend * blend) / 1.04;
        }
        for (const [cx, cy, rx, ry] of [
          [-0.16, 0.17, 0.205, 0.21],
          [0.16, -0.23, 0.16, 0.24],
          [0.19, 0.47, 0.115, 0.082],
          [-0.4, -0.29, 0.09, 0.11],
        ]) {
          const hole =
            Math.hypot((u - cx - 0.19 * pz) / rx, (v - cy + 0.21 * pz) / ry) -
            1;
          body = Math.min(body, hole * 0.42);
        }
        const flute =
          0.09 * Math.sin(33 * u + 5 * Math.sin(v * 6 + phase) + 8 * pz);
        iso.setCell(x, y, z, body + flute + 0.047 * Math.cos(v * 32 + u * 13));
      }
  iso.update();
  const g = new T.BufferGeometry();
  g.setAttribute(
    "position",
    new T.BufferAttribute(iso.positionArray.slice(0, iso.count * 3), 3),
  );
  g.setAttribute(
    "normal",
    new T.BufferAttribute(iso.normalArray.slice(0, iso.count * 3), 3),
  );
  g.normalizeNormals();
  iso.geometry.dispose();
  const p = g.attributes.position,
    n = g.attributes.normal;
  const uv = new Float32Array(p.count * 2),
    colors = new Float32Array(p.count * 3);
  const limestone = new T.Color(0xc6cbc0),
    damp = new T.Color(0x7b817d),
    moss = new T.Color(0x828a58);
  const tint = new T.Color();
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i),
      y = p.getY(i),
      z = p.getZ(i);
    uv[i * 2] = x * 1.8 + 0.41 * z;
    uv[i * 2 + 1] = y * 2.2 - 0.27 * z;
    const strata =
      0.5 + 0.5 * Math.cos(y * 24 + 3 * Math.sin(5 * x + phase) + z * 7);
    tint.copy(damp).lerp(limestone, 0.38 + 0.32 * strata + 0.23 * n.getY(i));
    tint
      .lerp(moss, 0.48 * Math.max(0, n.getY(i)) * strata)
      .toArray(colors, i * 3);
  }
  g.setAttribute("uv", new T.BufferAttribute(uv, 2));
  g.setAttribute("color", new T.BufferAttribute(colors, 3));
  return g;
}

/** Peltate leaves cup around a central attachment. Radial ribs converge there
 * and lift the scalloped rim, which catches light even on an overcast court. */
function lotusLeaf() {
  const g = new T.PlaneGeometry(1, 1, 56, 12);
  const p = g.attributes.position,
    uv = g.attributes.uv,
    colors = new Float32Array(p.count * 3);
  const base = new T.Color(0x54816e),
    rim = new T.Color(0x97a879),
    tint = new T.Color();
  for (let i = 0; i < p.count; i++) {
    const a = tau * uv.getX(i),
      r = 0.008 + 0.992 * uv.getY(i);
    const edge = 0.97 + 0.04 * Math.cos(9 * a) + 0.046 * Math.sin(5 * a + 0.8);
    const ribs = (0.5 + 0.5 * Math.cos(14 * a)) ** 4;
    const rr = r * edge;
    p.setXYZ(
      i,
      rr * Math.cos(a),
      -0.1 +
        0.2 * r ** 1.7 +
        0.057 * Math.cos(5 * a) * r ** 3 +
        0.026 * ribs * r,
      rr * Math.sin(a) * 0.92,
    );
    tint
      .copy(base)
      .lerp(rim, 0.22 * r + 0.46 * ribs * r)
      .multiplyScalar(0.8 + 0.2 * r)
      .toArray(colors, 3 * i);
  }
  g.setAttribute("color", new T.BufferAttribute(colors, 3));
  g.computeVertexNormals();
  return g;
}

function blossom() {
  const petals: T.BufferGeometry[] = [];
  for (let ring = 0; ring < 3; ring++) {
    const count = 9 - ring * 2;
    for (let j = 0; j < count; j++) {
      const g = new T.PlaneGeometry(1, 1, 4, 7);
      const p = g.attributes.position,
        uv = g.attributes.uv,
        colors = new Float32Array(p.count * 3);
      const a = (tau * (j + ring * 0.46)) / count;
      const root = new T.Color(0xc49670),
        ivory = new T.Color(0xf2dcc8),
        tip = new T.Color(0xbf707b);
      const tint = new T.Color();
      for (let i = 0; i < p.count; i++) {
        const v = uv.getY(i),
          u = uv.getX(i) * 2 - 1;
        const w =
          (0.016 + Math.sin(Math.PI * v) ** 0.8) * u * (0.092 - ring * 0.015);
        const reach =
          0.021 +
          v * (0.248 - ring * 0.073) -
          0.026 * u * u * Math.sin(Math.PI * v);
        p.setXYZ(
          i,
          reach * Math.cos(a) - w * Math.sin(a),
          v * (0.17 + 0.055 * ring) +
            0.073 * Math.sin(Math.PI * v) +
            0.031 * u * u * Math.sin(Math.PI * v),
          reach * Math.sin(a) + w * Math.cos(a),
        );
        tint
          .copy(root)
          .lerp(ivory, Math.min(1, v * 3))
          .lerp(tip, 0.65 * v ** 3 + 0.12 * Math.abs(u))
          .toArray(colors, 3 * i);
      }
      g.setAttribute("color", new T.BufferAttribute(colors, 3));
      g.computeVertexNormals();
      petals.push(g);
    }
  }
  const bloom = mergeGeometries(petals);
  petals.forEach((p) => p.dispose());
  return bloom;
}

export function lotusGarden(
  waterMaterial: T.Material,
  stone: T.MeshStandardMaterial,
  cliff: T.Texture,
  rand: () => number,
) {
  const banks = new T.Group(),
    pools = new T.Group();
  banks.name = "Scholar rocks and lotus beds";
  pools.name = "Garden pools";
  const limestone = stone.clone();
  limestone.map = cliff;
  limestone.bumpMap = cliff;
  limestone.bumpScale = 0.085;
  limestone.color.setHex(0xf3eee5);
  limestone.vertexColors = true;
  limestone.roughness = 0.76;
  limestone.normalScale.set(0.34, 0.34);
  const stones = [piercedStone(0, limestone), piercedStone(2.5, limestone)];
  const leaf = lotusLeaf(),
    flower = blossom();
  const foliage = new T.MeshStandardMaterial({
    vertexColors: true,
    side: T.DoubleSide,
    roughness: 0.72,
  });
  const petal = new T.MeshStandardMaterial({
    vertexColors: true,
    side: T.DoubleSide,
    roughness: 0.65,
  });
  const stalk = new T.MeshStandardMaterial({
    color: 0x677850,
    roughness: 0.84,
  });
  const patches: T.Matrix4[] = [],
    flowers: T.Matrix4[] = [],
    stalks: T.Matrix4[] = [];
  const dummy = new T.Object3D(),
    up = new T.Vector3(0, 1, 0);
  const stem = (a: T.Vector3, b: T.Vector3, r: number) => {
    const dir = b.clone().sub(a);
    dummy.position.copy(a).lerp(b, 0.5);
    dummy.scale.set(r, dir.length(), r);
    dummy.quaternion.setFromUnitVectors(up, dir.normalize());
    dummy.updateMatrix();
    stalks.push(dummy.matrix.clone());
  };
  for (const side of [-1, 1]) {
    const pool = new T.PlaneGeometry(1, 1, 52, 1);
    const p = pool.attributes.position,
      uv = pool.attributes.uv;
    for (let i = 0; i < p.count; i++) {
      const v = basinPoint(uv.getX(i), uv.getY(i), side, 0.011);
      p.setXYZ(i, v.x, v.y, v.z);
    }
    pool.computeVertexNormals();
    const water = new T.Mesh(pool, waterMaterial);
    water.receiveShadow = true;
    pools.add(water);
    const coping: T.BufferGeometry[] = [];
    for (const depth of [0, 1]) {
      for (let i = 0; i < 38; i++) {
        const a = basinPoint(i / 38, depth, side, 0),
          b = basinPoint((i + 1) / 38, depth, side, 0);
        const mid = a.clone().lerp(b, 0.5),
          h = 0.17 + rand() * 0.085;
        const block = new T.CylinderGeometry(1, 1.08, h, 8).rotateY(
          Math.PI / 8,
        );
        block.scale(a.distanceTo(b) * 0.57, 1, 0.21 + rand() * 0.14);
        block.rotateY(Math.atan2(a.z - b.z, b.x - a.x));
        block.translate(mid.x, h * 0.35, mid.z);
        coping.push(block);
      }
    }
    const kerb = new T.Mesh(mergeGeometries(coping), stone);
    kerb.castShadow = kerb.receiveShadow = true;
    banks.add(kerb);
    coping.forEach((g) => g.dispose());
    for (const [k, t, depth, height, yaw] of [
      [0, 0.22, 0.71, 3.1, -0.35],
      [1, 0.32, 0.62, 1.55, 0.4],
      [1, 0.71, 0.7, 2.65, 0.59],
      [0, 0.77, 0.53, 1.28, -0.83],
    ]) {
      const h = height * (side === 1 ? 0.8 : 1),
        pos = basinPoint(t + (side === 1 ? 0.135 : 0), depth, side, 0);
      const rock = new T.Mesh(stones[k], limestone);
      rock.position.set(pos.x, h * 0.88, pos.z);
      rock.scale.set(h * (k === 1 ? 0.9 : 0.72), h, h * 0.79);
      rock.rotation.y = side * yaw;
      rock.castShadow = rock.receiveShadow = true;
      banks.add(rock);
    }
    for (let clump = 0; clump < 19; clump++) {
      const t = 0.055 + rand() * 0.89,
        depth = 0.22 + 0.55 * rand();
      const base = basinPoint(t, depth, side, 0.016);
      for (let j = 0; j < 6; j++) {
        const a = rand() * tau,
          span = rand() * 0.78,
          size = 0.22 + 0.32 * rand();
        const pos = base
          .clone()
          .add(
            new T.Vector3(
              span * Math.cos(a),
              0.09 + rand() ** 1.5 * 0.81,
              span * Math.sin(a),
            ),
          );
        stem(base, pos, 0.011 + size * 0.013);
        dummy.position.copy(pos);
        dummy.rotation.set((rand() - 0.5) * 0.95, a, (rand() - 0.5) * 0.77);
        dummy.scale.setScalar(size);
        dummy.updateMatrix();
        patches.push(dummy.matrix.clone());
      }
      if (clump % 3 !== 0) {
        const pos = base
          .clone()
          .add(new T.Vector3(rand() - 0.5, 0.63 + rand() * 0.57, rand() - 0.5));
        stem(base, pos, 0.015);
        dummy.position.copy(pos);
        dummy.rotation.set(0.12, rand() * tau, -0.12);
        dummy.scale.setScalar(0.75 + rand() * 0.62);
        dummy.updateMatrix();
        flowers.push(dummy.matrix.clone());
      }
    }
  }
  for (const [g, m, matrices] of [
    [leaf, foliage, patches],
    [flower, petal, flowers],
    [new T.CylinderGeometry(0.72, 1, 1, 6), stalk, stalks],
  ] as const) {
    const inst = new T.InstancedMesh(g, m, matrices.length);
    matrices.forEach((matrix, i) => inst.setMatrixAt(i, matrix));
    inst.castShadow = inst.receiveShadow = true;
    banks.add(inst);
  }
  return { banks, pools };
}
