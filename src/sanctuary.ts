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
export function courtyardMaple(
  random: () => number,
  bark: T.Material,
  copper: boolean,
) {
  const tree = new T.Group(),
    branches: T.BufferGeometry[] = [],
    tips: T.Vector3[] = [];
  function branch(
    start: T.Vector3,
    direction: T.Vector3,
    length: number,
    radius: number,
    depth: number,
  ) {
    const end = start.clone().addScaledVector(direction, length);
    const mid = start.clone().lerp(end, 0.53);
    mid.y -= length * 0.09;
    const path = new T.CatmullRomCurve3([start, mid, end]);
    const stem = new T.TubeGeometry(path, 5, radius, 7, false);
    const pos = stem.attributes.position;
    for (let j = 0; j <= 5; j++) {
      const c = path.getPointAt(j / 5);
      for (let k = 0; k < 8; k++) {
        const p = j * 8 + k,
          v = new T.Vector3()
            .fromBufferAttribute(pos, p)
            .lerp(c, (0.47 * j) / 5);
        pos.setXYZ(p, v.x, v.y, v.z);
      }
    }
    stem.computeVertexNormals();
    branches.push(stem);
    if (depth === 0) {
      tips.push(mid, end);
      return;
    }
    const azimuth = random() * Math.PI * 2;
    for (let i = 0; i < 3; i++) {
      const a = azimuth + i * 2.094 + random() * 0.4;
      const next = new T.Vector3(
        Math.cos(a),
        0.09 + random() * 0.58,
        Math.sin(a),
      )
        .addScaledVector(direction, 0.82)
        .normalize();
      branch(
        i === 0 ? mid : end,
        next,
        length * (0.54 + random() * 0.22),
        radius * 0.53,
        depth - 1,
      );
    }
  }
  branch(
    new T.Vector3(),
    new T.Vector3(0.22, 1, 0.09).normalize(),
    4.1,
    0.32,
    4,
  );
  const wood = new T.Mesh(mergeGeometries(branches), bark);
  branches.forEach((g) => g.dispose());
  wood.castShadow = wood.receiveShadow = true;
  tree.add(wood);
  const shape = new T.Shape();
  shape.moveTo(0, -0.5);
  for (const [x, y] of [
    [-0.16, -0.12],
    [-0.49, 0.12],
    [-0.24, 0.16],
    [-0.43, 0.46],
    [-0.12, 0.29],
    [0, 0.71],
    [0.13, 0.28],
    [0.44, 0.44],
    [0.25, 0.13],
    [0.49, 0.12],
    [0.15, -0.15],
    [0, -0.5],
  ])
    shape.lineTo(x, y);
  const leaf = new T.ShapeGeometry(shape);
  const foliage = new T.InstancedMesh(
    leaf,
    new T.MeshStandardMaterial({ side: T.DoubleSide, roughness: 0.82 }),
    tips.length * 18 + 110,
  );
  const dummy = new T.Object3D(),
    color = new T.Color();
  let n = 0;
  function placeLeaf(ground: boolean) {
    dummy.rotation.set(
      ground ? -Math.PI / 2 : -random() * 2,
      ground ? 0 : random() * 3,
      random() * 6,
    );
    dummy.scale.setScalar((ground ? 0.14 : 0.2) + random() * 0.18);
    dummy.updateMatrix();
    foliage.setMatrixAt(n, dummy.matrix);
    color.setHSL(
      (copper ? 0.006 : 0.055) + random() * 0.055,
      0.52 + random() * 0.27,
      0.12 + random() * 0.27,
    );
    foliage.setColorAt(n++, color);
  }
  for (const tip of tips)
    for (let j = 0; j < 18; j++) {
      dummy.position.copy(tip);
      dummy.position.x += (random() - 0.5) * 1.38;
      dummy.position.z += (random() - 0.5) * 1.32;
      dummy.position.y += (random() - 0.5) * 0.8;
      placeLeaf(false);
    }
  for (let j = 0; j < 110; j++) {
    dummy.position.set(
      (random() - 0.5) * 9,
      0.012 + random() * 0.02,
      (random() - 0.5) * 9,
    );
    placeLeaf(true);
  }
  foliage.receiveShadow = true;
  tree.add(foliage);
  return tree;
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
