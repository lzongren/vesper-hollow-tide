import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** The distant valley is cylindrical so an orbit cannot run off its edges. */
export function valleyHorizon(texture: T.Texture, encounter: number) {
  texture.wrapS = T.MirroredRepeatWrapping;
  texture.repeat.x = 4;
  const material = new T.MeshBasicMaterial({
    map: texture,
    color: [0xa2aab7, 0xb3c4ba, 0x948077][encounter],
    side: T.BackSide,
    fog: false,
    depthWrite: false,
  });
  const sky = new T.Mesh(
    new T.CylinderGeometry(104, 104, 62, 160, 1, true),
    material,
  );
  sky.position.y = 12;
  sky.rotation.y = 0.64;
  sky.renderOrder = -20;
  return sky;
}

/** Different panels meet at angled hinges. Each carries only its part of the motif. */
export function foldingScreen(
  material: T.Material,
  trim: T.Material,
  width: number,
  height: number,
  folds: number,
) {
  const screen = new T.Group();
  const frames: T.BufferGeometry[] = [];
  const span = width / folds;
  for (let i = 0; i < folds; i++) {
    const angle = (i % 2 ? 1 : -1) * 0.2;
    const x =
      (i + 0.5) * span * Math.cos(angle) - (width * Math.cos(angle)) / 2;
    const face = new T.PlaneGeometry(span, height, 24, 30);
    const uv = face.attributes.uv;
    for (let p = 0; p < uv.count; p++) uv.setX(p, (i + uv.getX(p)) / folds);
    const mesh = new T.Mesh(face, material);
    mesh.receiveShadow = mesh.castShadow = true;
    mesh.rotation.y = angle;
    mesh.position.x = x;
    screen.add(mesh);
    for (const y of [-height / 2, height / 2]) {
      frames.push(
        new T.BoxGeometry(span + 0.025, 0.1, 0.13)
          .translate(0, y, 0.025)
          .rotateY(angle)
          .translate(x, 0, 0),
      );
    }
    frames.push(
      new T.BoxGeometry(0.055, height, 0.12)
        .translate(-span / 2, 0, 0.025)
        .rotateY(angle)
        .translate(x, 0, 0),
    );
    if (i === folds - 1)
      frames.push(
        new T.BoxGeometry(0.055, height, 0.12)
          .translate(span / 2, 0, 0.025)
          .rotateY(angle)
          .translate(x, 0, 0),
      );
  }
  const frame = new T.Mesh(mergeGeometries(frames), trim);
  frames.forEach((g) => g.dispose());
  frame.castShadow = frame.receiveShadow = true;
  screen.add(frame);
  return screen;
}

/** Branches, individual lobed leaves and windfall share three draw calls per tree. */
/** Build each crown from the branch tips. Leaves occur in opposite pairs on
 * drooping shoots, with longer open spaces between the primary limbs. */
export function courtyardMaple(
  random: () => number,
  bark: T.Material,
  copper: boolean,
  leaf: T.BufferGeometry,
  map: T.Texture,
  clock: { value: number },
) {
  const tree = new T.Group(),
    stems: T.BufferGeometry[] = [],
    shoots: T.CatmullRomCurve3[] = [];
  const lean = random() * 0.75 - 0.375,
    spread = 0.8 + random() * 0.55;
  const rot = random() * Math.PI * 2;
  function stem(
    path: T.CatmullRomCurve3,
    r0: number,
    r1: number,
    segments: number,
    sides: number,
  ) {
    const g = new T.TubeGeometry(path, segments, r0, sides, false),
      p = g.attributes.position;
    for (let j = 0; j <= segments; j++) {
      const center = path.getPointAt(j / segments);
      for (let k = 0; k <= sides; k++) {
        const n = j * (sides + 1) + k;
        const v = new T.Vector3()
          .fromBufferAttribute(p, n)
          .lerp(center, ((1 - r1 / r0) * j) / segments);
        p.setXYZ(n, v.x, v.y, v.z);
      }
    }
    g.computeVertexNormals();
    stems.push(g);
  }
  function grow(
    from: T.Vector3,
    dir: T.Vector3,
    len: number,
    r: number,
    depth: number,
  ) {
    const end = from.clone().addScaledVector(dir, len);
    end.x += Math.cos(rot) * len * lean * 0.17;
    const mid = from.clone().lerp(end, 0.56);
    mid.x += Math.sin(rot + depth) * len * 0.13;
    mid.y += len * (depth ? -0.08 : 0.115);
    const curve = new T.CatmullRomCurve3([from, mid, end]);
    stem(curve, r, r * (depth ? 0.53 : 0.19), depth ? 5 : 3, depth ? 7 : 3);
    if (depth === 0) {
      shoots.push(curve);
      return;
    }
    const baseAngle = Math.atan2(dir.z, dir.x),
      offset = random() * 0.8;
    const forks = depth > 1 ? 3 : 4;
    for (let i = 0; i < forks; i++) {
      const az =
        baseAngle + offset + (Math.PI * 2 * i) / forks + random() * 0.52;
      const next = new T.Vector3(
        Math.cos(az) * spread,
        depth > 1 ? 0.23 + random() * 0.85 : -0.55 + random() * 0.67,
        Math.sin(az) * spread,
      )
        .addScaledVector(dir, depth > 1 ? 0.82 : 0.55)
        .normalize();
      grow(
        curve.getPoint(0.4 + (0.57 / forks) * i + random() * 0.08),
        next,
        len * (0.53 + random() * (depth === 1 ? 0.56 : 0.28)),
        r * (0.41 + random() * 0.15),
        depth - 1,
      );
    }
  }
  grow(
    new T.Vector3(),
    new T.Vector3(lean, 1, -0.16 + random() * 0.32).normalize(),
    3.9 + random() * 0.9,
    0.27 + random() * 0.09,
    4,
  );
  const wood = new T.Mesh(mergeGeometries(stems), bark);
  stems.forEach((s) => s.dispose());
  wood.castShadow = wood.receiveShadow = true;
  tree.add(wood);
  const material = new T.MeshStandardMaterial({
    map,
    side: T.DoubleSide,
    roughness: 0.79,
    alphaTest: 0.42,
    metalness: 0,
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.breezeTime = clock;
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        "#include <common>\nuniform float breezeTime;",
      )
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
      float t=breezeTime*1.45+dot(instanceMatrix[3].xz,vec2(.91,.73));
      transformed.z+=uv.y*uv.y*(.13*sin(t)+.058*sin(2.4*t));`,
      );
  };
  const pairs = 9,
    foliage = new T.InstancedMesh(leaf, material, shoots.length * pairs * 2);
  const dummy = new T.Object3D(),
    color = new T.Color();
  let n = 0;
  for (const shoot of shoots) {
    const tint = random(),
      turn = random() * 6.28;
    for (let j = 0; j < pairs; j++) {
      const t = 0.1 + (0.85 * j) / (pairs - 1),
        origin = shoot.getPoint(t),
        tangent = shoot.getTangent(t);
      const az = Math.atan2(tangent.x, tangent.z);
      for (const side of [-1, 1]) {
        dummy.position.copy(origin);
        dummy.rotation.order = "YXZ";
        dummy.rotation.set(
          1.28 + random() * 0.59,
          az + side * (0.81 + random() * 0.47),
          0.32 * Math.sin(turn + j * 0.52),
        );
        dummy.scale.setScalar((0.25 + random() * 0.12) * (1 - 0.27 * t));
        dummy.updateMatrix();
        foliage.setMatrixAt(n, dummy.matrix);
        color.setRGB(
          copper ? 0.58 + tint * 0.6 : 0.43 + tint * 0.4,
          copper ? 0.37 + tint * 0.51 + random() * 0.11 : 0.69 + tint * 0.36,
          copper ? 0.23 + tint * 0.38 : 0.32 + tint * 0.35,
        );
        foliage.setColorAt(n++, color);
      }
    }
  }
  foliage.userData.sharedGeometry = true;
  foliage.receiveShadow = true;
  tree.add(foliage);
  return tree;
}

/** Trace the alpha silhouette into a fan so depth-only passes also see the
 * indentations between the lobes. Keep the petiole at the shoot attachment. */
export function mapleLeaf(texture: T.Texture) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 192;
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(texture.image as HTMLImageElement, 0, 0, 192, 192);
  const alpha = ctx.getImageData(0, 0, 192, 192).data;
  let top = 191,
    base = 0,
    pivot = 96;
  for (let y = 0; y < 192; y++) {
    let count = 0,
      sum = 0;
    for (let x = 0; x < 192; x++)
      if (alpha[(y * 192 + x) * 4 + 3] > 150) {
        count++;
        sum += x;
      }
    if (count) {
      top = Math.min(top, y);
      base = y;
      pivot = sum / count;
    }
  }
  const cx = 96,
    cy = Math.round(top + (base - top) * 0.728);
  const positions: number[] = [],
    uvs: number[] = [],
    indices: number[] = [];
  function point(x: number, y: number) {
    const u = x / 191,
      v = 1 - y / 191;
    positions.push(
      (x - pivot) / (base - top),
      (base - y) / (base - top),
      0.11 * Math.abs((x - cx) / 191) + 0.048 * Math.sin(4.3 * v),
    );
    uvs.push(u, v);
  }
  point(cx, cy);
  for (let i = 0; i < 44; i++) {
    const a = (i / 44) * Math.PI * 2,
      dx = Math.cos(a),
      dy = Math.sin(a);
    let radius = 0;
    for (let r = 1; r < 192; r++) {
      const x = Math.round(cx + dx * r),
        y = Math.round(cy + dy * r);
      if (x < 0 || x >= 192 || y < 0 || y >= 192) break;
      if (alpha[(192 * y + x) * 4 + 3] > 100) radius = r;
    }
    point(cx + dx * (radius + 1), cy + dy * (radius + 1));
    indices.push(0, 1 + ((i + 1) % 44), i + 1);
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute("position", new T.Float32BufferAttribute(positions, 3));
  geo.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}
/** Fit the silhouette as well as the UVs; the SSAO depth pass ignores alpha tests. */
export function featherGeometry(
  texture: T.Texture,
  width: number,
  length: number,
) {
  const canvas = document.createElement("canvas");
  canvas.width = 96;
  canvas.height = 96;
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(texture.image as HTMLImageElement, 0, 0, 96, 96);
  const alpha = ctx.getImageData(0, 0, 96, 96).data;
  const vertices: number[] = [],
    uvs: number[] = [],
    indices: number[] = [];
  for (let row = 0; row <= 32; row++) {
    const y = Math.round((row * 95) / 32);
    let left = 95,
      right = 0;
    for (let x = 0; x < 96; x++)
      if (alpha[(y * 96 + x) * 4 + 3] > 120) {
        left = Math.min(left, x);
        right = Math.max(right, x);
      }
    if (right < left) left = right = row < 16 ? 52 : 45;
    const v = 1 - row / 32;
    for (let j = 0; j < 4; j++) {
      const u = (left - 1 + ((right - left + 2) * j) / 3) / 95;
      uvs.push(u, v);
      vertices.push((u - 0.5) * width, (v - 0.5) * length, 0.08 * v * v);
    }
    if (row)
      for (let j = 0; j < 3; j++) {
        const i = (row - 1) * 4 + j;
        indices.push(i, i + 4, i + 1, i + 1, i + 4, i + 5);
      }
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.Float32BufferAttribute(vertices, 3));
  geometry.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

export function leafDrifts(random: () => number, amber: boolean) {
  const shape = new T.Shape();
  shape.moveTo(0, -0.51);
  for (const [x, y] of [
    [-0.2, -0.04],
    [-0.47, 0.17],
    [-0.18, 0.14],
    [-0.38, 0.46],
    [-0.1, 0.31],
    [0, 0.66],
    [0.11, 0.28],
    [0.4, 0.46],
    [0.22, 0.12],
    [0.5, 0.16],
    [0.18, -0.12],
    [0, -0.51],
  ])
    shape.lineTo(x, y);
  const leaves = new T.InstancedMesh(
    new T.ShapeGeometry(shape),
    new T.MeshStandardMaterial({ side: T.DoubleSide, roughness: 0.79 }),
    540,
  );
  const dummy = new T.Object3D(),
    color = new T.Color();
  for (let cluster = 0; cluster < 18; cluster++) {
    const angle = random() * Math.PI * 2,
      r = 4.3 + random() * 9;
    for (let i = 0; i < 30; i++) {
      const a = angle + (random() - 0.5) * 0.7,
        distance = r + (random() - 0.5) * 1.15;
      dummy.position.set(
        Math.sin(a) * distance,
        0.01 + random() * 0.023,
        Math.cos(a) * distance,
      );
      dummy.scale.setScalar(0.058 + random() * 0.117);
      dummy.rotation.set(-Math.PI / 2 + random() * 0.16, 0, random() * 6);
      dummy.updateMatrix();
      const slot = cluster * 30 + i;
      leaves.setMatrixAt(slot, dummy.matrix);
      leaves.setColorAt(
        slot,
        color.setHSL(
          (amber ? 0.055 : 0.006) + random() * 0.055,
          0.5 + random() * 0.25,
          0.115 + random() * 0.17,
        ),
      );
    }
  }
  leaves.receiveShadow = true;
  return leaves;
}
