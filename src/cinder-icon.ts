import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

type Point = [number, number, number];
const tau = Math.PI * 2;
const bell = (v: number, w: number) => Math.exp(-((v / w) ** 2));

/** Lost-wax bronze face, a pierced flame mandorla and a patchwork outer robe.
 * Each group uses actor-space metres and has its own animated attachment. */
export function cinderIcon(brocade?: T.Texture) {
  const bronze = new T.MeshStandardMaterial({
    name: "Smoke-dark cast bronze",
    color: 0xede4cc,
    vertexColors: true,
    metalness: 0.31,
    roughness: 0.57,
    side: T.DoubleSide,
  });
  const brass = new T.MeshStandardMaterial({
    name: "Worn gilding",
    color: 0xc29b59,
    metalness: 0.67,
    roughness: 0.41,
  });
  const recess = new T.MeshStandardMaterial({
    name: "Oxidized recess",
    color: 0x55483b,
    metalness: 0.34,
    roughness: 0.71,
    side: T.DoubleSide,
  });
  const coal = new T.MeshStandardMaterial({
    name: "Banked ember",
    color: 0x9f4826,
    emissive: 0xf78032,
    emissiveIntensity: 0.62,
    roughness: 0.58,
  });
  const robeMat = new T.MeshStandardMaterial({
    name: "Madder and smoke silk",
    map: brocade ?? null,
    bumpMap: brocade ?? null,
    bumpScale: 0.0025,
    vertexColors: true,
    side: T.DoubleSide,
    roughness: 0.81,
    metalness: 0.035,
  });
  const piles = new Map<T.Material, T.BufferGeometry[]>();
  function add(m: T.Material, g: T.BufferGeometry) {
    const flat = g.index ? g.toNonIndexed() : g;
    if (flat !== g) g.dispose();
    if (!piles.has(m)) piles.set(m, []);
    piles.get(m)!.push(flat);
  }
  function flush(name: string) {
    const group = new T.Group();
    group.name = name;
    for (const [mat, parts] of piles) {
      const mesh = new T.Mesh(mergeGeometries(parts), mat);
      mesh.name = mat.name;
      mesh.castShadow = mesh.receiveShadow = true;
      group.add(mesh);
      parts.forEach((p) => p.dispose());
    }
    piles.clear();
    return group;
  }
  function wire(m: T.Material, pts: Point[], r: number, closed = false) {
    const path = new T.CatmullRomCurve3(
      pts.map((v) => new T.Vector3(...v)),
      closed,
    );
    add(
      m,
      new T.TubeGeometry(path, Math.max(16, pts.length * 3), r, 6, closed),
    );
  }
  function bead(
    m: T.Material,
    x: number,
    y: number,
    z: number,
    rx: number,
    ry: number,
    rz: number,
  ) {
    add(
      m,
      new T.SphereGeometry(1, 16, 12).scale(rx, ry, rz).translate(x, y, z),
    );
  }
  const color = (rgb: number) => new T.Color(rgb);
  const base = color(0xc2ad89),
    ash = color(0x7c7363),
    patina = color(0x586b60),
    tint = new T.Color();
  // All features use the same relief as the shell. This keeps the eyelids and
  // lip edge on the cheek instead of floating above it at oblique angles.
  const width = (y: number) =>
    0.283 *
    (0.58 + 0.42 * T.MathUtils.smoothstep(y, -0.31, -0.08)) *
    Math.sqrt(Math.max(0.015, 1 - ((y - 0.025) / 0.36) ** 2));
  const front = (x: number, y: number) => {
    const abs = Math.abs(x),
      eye = y - 0.054 - 0.12 * (abs - 0.115);
    return (
      0.386 +
      0.095 * Math.sqrt(Math.max(0, 1 - (x / width(y)) ** 2)) +
      0.024 * bell(y - 0.2, 0.11) -
      0.057 * bell(abs - 0.113, 0.068) * bell(eye, 0.054) +
      0.052 * bell(abs - 0.122, 0.081) * bell(eye - 0.065, 0.038) +
      0.046 * bell(abs - 0.158, 0.074) * bell(y + 0.042, 0.07) +
      0.068 * bell(x, 0.044) * bell(y - 0.011, 0.147) +
      0.094 * bell(x, 0.058) * bell(y + 0.067, 0.042) +
      0.037 * bell(abs - 0.055, 0.028) * bell(y + 0.079, 0.029) +
      0.03 * bell(x, 0.097) * bell(y + 0.16, 0.072) +
      0.04 * bell(x, 0.083) * bell(y + 0.254, 0.057)
    );
  };
  const face = new T.PlaneGeometry(1, 1, 84, 92),
    p = face.attributes.position,
    uv = face.attributes.uv;
  const rgb = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const y = -0.325 + 0.676 * uv.getY(i),
      x = (2 * uv.getX(i) - 1) * width(y);
    const z = front(x, y);
    p.setXYZ(i, x, y, z);
    const soot =
      0.22 +
      0.38 * (1 - bell(x, 0.205)) +
      0.19 * Math.sin(y * 36 + 2 * Math.cos(x * 19));
    const speckle = Math.sin(x * 631 + y * 239) * Math.sin(x * 379 - y * 491);
    tint
      .copy(base)
      .lerp(ash, soot)
      .lerp(patina, 0.23 * bell(Math.abs(x) - 0.19, 0.065))
      .multiplyScalar(0.97 + 0.07 * speckle)
      .toArray(rgb, 3 * i);
  }
  face.setAttribute("color", new T.BufferAttribute(rgb, 3));
  face.computeVertexNormals();
  add(bronze, face);
  function tracing(
    mat: T.Material,
    path: number[][],
    r: number,
    offset: number,
  ) {
    wire(
      mat,
      path.map(([x, y]) => [x, y, front(x, y) + offset]),
      r,
    );
  }
  for (const side of [-1, 1]) {
    const trace = (m: T.Material, points: number[][], r: number, z: number) =>
      tracing(
        m,
        points.map(([x, y]) => [side * x, y]),
        r,
        z,
      );
    trace(
      recess,
      [
        [0.053, 0.053],
        [0.082, 0.045],
        [0.117, 0.046],
        [0.151, 0.057],
        [0.18, 0.07],
      ],
      0.009,
      0.008,
    );
    trace(
      coal,
      [
        [0.093, 0.048],
        [0.108, 0.047],
        [0.125, 0.051],
      ],
      0.0048,
      0.017,
    );
    trace(
      brass,
      [
        [0.049, 0.062],
        [0.084, 0.061],
        [0.115, 0.06],
        [0.151, 0.066],
        [0.183, 0.077],
      ],
      0.008,
      0.012,
    );
    trace(
      recess,
      [
        [0.049, 0.102],
        [0.091, 0.122],
        [0.132, 0.136],
        [0.17, 0.134],
        [0.204, 0.118],
      ],
      0.008,
      0.003,
    );
    trace(
      recess,
      [
        [0.023, -0.083],
        [0.041, -0.09],
        [0.058, -0.085],
      ],
      0.006,
      0.004,
    );
    trace(
      recess,
      [
        [0.058, -0.104],
        [0.081, -0.124],
        [0.101, -0.162],
      ],
      0.003,
      0.004,
    );
    trace(
      brass,
      [
        [0.009, -0.156],
        [0.034, -0.151],
        [0.061, -0.16],
        [0.084, -0.164],
      ],
      0.009,
      0.004,
    );
    trace(
      recess,
      [
        [0, -0.17],
        [0.038, -0.171],
        [0.067, -0.166],
        [0.088, -0.164],
      ],
      0.0045,
      0.009,
    );
    // A broken trail of gilding follows a fracture from temple to cheek.
    trace(
      recess,
      [
        [0.214, 0.16],
        [0.195, 0.109],
        [0.212, 0.078],
        [0.196, 0.046],
        [0.199, 0.012],
        [0.175, -0.031],
      ],
      0.004,
      0.002,
    );
    trace(
      brass,
      [
        [0.196, 0.046],
        [0.182, 0.048],
        [0.171, 0.023],
      ],
      0.0023,
      0.004,
    );
    const hx = side * 0.26;
    bead(recess, hx, 0.009, 0.31, 0.058, 0.085, 0.043);
    add(
      brass,
      new T.TorusGeometry(0.068, 0.009, 8, 36)
        .scale(0.68, 1.15, 1)
        .translate(hx, -0.073, 0.345),
    );
    bead(recess, hx, -0.161, 0.345, 0.022, 0.03, 0.02);
  }
  tracing(
    brass,
    [
      [-0.055, -0.182],
      [-0.027, -0.19],
      [0, -0.191],
      [0.033, -0.186],
      [0.061, -0.177],
    ],
    0.006,
    0.003,
  );
  bead(brass, 0, 0.164, front(0, 0.164) + 0.009, 0.022, 0.028, 0.01);
  bead(coal, 0, 0.164, front(0, 0.164) + 0.019, 0.011, 0.016, 0.006);
  // A gilt diadem and five repoussé lotus leaves follow the brow.
  for (let ring = 0; ring < 2; ring++) {
    const pts: Point[] = Array.from({ length: 37 }, (_, i) => {
      const a = (i / 36 - 0.5) * Math.PI;
      return [
        0.252 * Math.sin(a),
        0.208 + 0.049 * ring + 0.04 * Math.cos(a),
        0.256 + 0.24 * Math.cos(a),
      ];
    });
    wire(brass, pts, ring ? 0.01 : 0.014);
  }
  for (let j = -2; j <= 2; j++) {
    const a = j * 0.53;
    const leaf = new T.Shape();
    leaf.moveTo(-0.052, 0);
    leaf.quadraticCurveTo(-0.088, 0.081, 0, 0.161);
    leaf.quadraticCurveTo(0.086, 0.074, 0.052, 0);
    leaf.closePath();
    const g = new T.ExtrudeGeometry(leaf, {
      depth: 0.012,
      bevelSize: 0.004,
      bevelThickness: 0.005,
      bevelSegments: 2,
      curveSegments: 12,
    });
    g.rotateZ(-a * 0.21)
      .rotateY(a)
      .translate(0.245 * Math.sin(a), 0.238, 0.255 + 0.23 * Math.cos(a));
    add(brass, g);
    bead(
      recess,
      0.259 * Math.sin(a),
      0.304,
      0.26 + 0.245 * Math.cos(a),
      0.02,
      0.029,
      0.016,
    );
  }
  const mask = flush("Smoke-gilt votive face");

  // The open tongues run between two concentric rims. Firelight can pass
  // through the hollow body and pick out the turned edges at combat distance.
  for (const [r, thick, m] of [
    [0.63, 0.023, recess],
    [0.69, 0.016, brass],
    [0.75, 0.026, recess],
    [0.77, 0.01, brass],
  ] as const)
    add(m, new T.TorusGeometry(r, thick, 8, 104));
  for (let i = 0; i < 27; i++) {
    const a = (tau * i) / 27;
    const point = (x: number, y: number, z: number): Point => [
      (0.744 + y) * Math.sin(a) + x * Math.cos(a),
      (0.744 + y) * Math.cos(a) - x * Math.sin(a),
      z,
    ];
    const h =
      0.135 + 0.12 * (0.5 + 0.5 * Math.cos(a)) + 0.052 * (i % 3 === 0 ? 1 : 0);
    const shape = new T.Shape();
    shape.moveTo(-0.076, 0);
    shape.bezierCurveTo(-0.088, 0.09, -0.012, h * 0.7, -0.033, h);
    shape.bezierCurveTo(0.047, h * 0.78, 0.086, h * 0.39, 0.061, 0);
    shape.closePath();
    const hole = new T.Path();
    hole.moveTo(-0.03, 0.035);
    hole.quadraticCurveTo(-0.038, 0.079, -0.013, h * 0.71);
    hole.quadraticCurveTo(0.043, 0.088, 0.03, 0.035);
    hole.closePath();
    shape.holes.push(hole);
    const g = new T.ExtrudeGeometry(shape, {
      depth: 0.014,
      bevelSize: 0.003,
      bevelThickness: 0.003,
      bevelSegments: 1,
      curveSegments: 10,
    });
    g.translate(0, 0.744, -0.015).rotateZ(-a);
    add(recess, g);
    wire(
      brass,
      [
        point(-0.071, 0, 0.008),
        point(-0.062, 0.07, 0.014),
        point(-0.024, h * 0.66, 0.012),
        point(-0.033, h, 0),
      ],
      0.0058,
    );
    bead(
      i % 3 === 0 ? coal : brass,
      ...point(0, -0.072, 0.012),
      0.017,
      0.018,
      0.01,
    );
  }
  const halo = flush("Pierced flame mandorla");
  // The stole descends from one shoulder to the opposite hip. The hem and
  // couching follow exactly the surface where folds catch on the raised chest.
  const cloth = (u: number, t: number): Point => {
    const half = 0.18 + 0.17 * Math.sin(t * Math.PI * 0.78);
    const x = 0.27 - 0.52 * t + u * half;
    const y = 2.9 - 1.23 * t + 0.16 * u - 0.13 * (1 - u * u) * (1 - t);
    const pleat =
      0.033 * Math.cos(u * 8 + 4 * t) * Math.sin(Math.PI * t) +
      0.016 * Math.cos(22 * t + 3 * u);
    const z = -0.16 - 1.45 * x * x - 0.35 * (1 - t) ** 5 + pleat;
    return [x, y, z];
  };
  const clothGeo = new T.PlaneGeometry(1, 1, 46, 76),
    cp = clothGeo.attributes.position,
    cu = clothGeo.attributes.uv;
  const threads = new Float32Array(cp.count * 3),
    madder = color(0xf4e2c7),
    rust = color(0xc6b8a8),
    border = color(0xf8eacb);
  for (let i = 0; i < cp.count; i++) {
    const u = 2 * cu.getX(i) - 1,
      t = 1 - cu.getY(i),
      [x, y, z] = cloth(u, t);
    cp.setXYZ(i, x, y, z);
    const band = Math.min(1 - Math.abs(u), Math.min(t, 1 - t) * 3);
    const warp = 0.5 + 0.5 * Math.sin(172 * t + 23 * u);
    const patch = (Math.floor((u + 1) * 2) + Math.floor(t * 6)) % 3;
    tint.copy(madder).lerp(rust, 0.19 * patch + 0.15 * warp);
    if (band < 0.086) tint.lerp(border, 0.52 + 0.2 * warp);
    tint
      .multiplyScalar(0.87 + 0.13 * Math.cos(24 * t + 3 * u))
      .toArray(threads, 3 * i);
  }
  clothGeo.setAttribute("color", new T.BufferAttribute(threads, 3));
  clothGeo.computeVertexNormals();
  add(robeMat, clothGeo);
  for (const u of [-0.98, 0.98])
    wire(
      brass,
      Array.from({ length: 37 }, (_, i) => {
        const p = cloth(u, i / 36);
        p[2] += 0.005;
        return p;
      }),
      0.0045,
    );
  // Turn the same width of silk over the shoulder and down the back.
  const back = new T.PlaneGeometry(1, 1, 42, 56),
    bp = back.attributes.position,
    bu = back.attributes.uv;
  const backColors = new Float32Array(bp.count * 3);
  for (let i = 0; i < bp.count; i++) {
    const u = bu.getX(i) * 2 - 1,
      t = 1 - bu.getY(i),
      [x, y, z] = cloth(u, 0);
    const roll = Math.min(1, t * 4),
      fall = Math.max(0, (t - 0.25) / 0.75);
    bp.setXYZ(
      i,
      x - 0.31 * fall + 0.07 * u * fall,
      y + 0.14 * Math.sin(roll * Math.PI) - 0.91 * fall,
      z - 0.38 * roll + 0.045 * Math.cos(7 * u + 4 * fall) * fall,
    );
    tint
      .copy(madder)
      .multiplyScalar(0.83 + 0.12 * Math.cos(7 * u + 4 * fall))
      .toArray(backColors, 3 * i);
  }
  back.setAttribute("color", new T.BufferAttribute(backColors, 3));
  back.computeVertexNormals();
  add(robeMat, back);
  // A necklace of uneven dark seeds sits above the crossed robe.
  for (let i = 0; i <= 24; i++) {
    const a = (i / 24 - 0.5) * Math.PI * 1.15,
      x = 0.336 * Math.sin(a),
      y = 2.78 - 0.38 * Math.cos(a),
      z = -0.38 + 0.34 * Math.cos(a);
    bead(i % 6 === 0 ? brass : recess, x, y, z, 0.03, 0.034, 0.029);
  }
  const stole = flush("Madder patchwork stole and prayer beads");
  // Ash-stained silk drops below the belt in three unequal tabs.
  for (let panel = 0; panel < 3; panel++) {
    const hem = new T.PlaneGeometry(1, 1, 16, 42),
      hp = hem.attributes.position,
      hu = hem.attributes.uv;
    const hues = new Float32Array(hp.count * 3);
    for (let i = 0; i < hp.count; i++) {
      const u = 2 * hu.getX(i) - 1,
        t = 1 - hu.getY(i);
      const x =
        (panel - 1) * 0.2 + 0.09 * u + 0.046 * Math.sin(2.8 * t + panel);
      const y =
        2.02 - (1.04 + 0.21 * (panel === 0 ? 1 : 0)) * t + 0.047 * u * t;
      const z =
        -0.23 + 0.17 * t - 0.75 * x * x + 0.019 * Math.cos(6 * u + 6 * t);
      hp.setXYZ(i, x, y, z);
      hu.setXY(i, 0.055 + (0.89 * (u + 1)) / 2, t);
      tint
        .copy(madder)
        .lerp(rust, 0.36 + 0.22 * t)
        .multiplyScalar(0.83 + 0.13 * Math.cos(6 * u + 6 * t))
        .toArray(hues, 3 * i);
    }
    hem.setAttribute("color", new T.BufferAttribute(hues, 3));
    hem.computeVertexNormals();
    add(robeMat, hem);
  }
  const tabs = flush("Three trailing brocade panels");
  return { mask, halo, stole, tabs, ember: coal };
}
