import * as T from "three";
import { ridgePavilion } from "./ridge-pavilion";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

type Spur = readonly [
  x: number,
  z: number,
  height: number,
  width: number,
  depth: number,
  yaw: number,
];
const spurs: Spur[][] = [
  [
    [-34, -47, 24, 13, 9, -0.4],
    [-25, -53, 17, 9, 9, 0.4],
    [35, -52, 28, 10, 12, 0.8],
    [44, -48, 18, 12, 10, 0.1],
    [-49, 14, 23, 10, 15, 0.3],
    [36, 32, 18, 12, 8, -0.5],
    [15, 63, 24, 16, 9, 0.3],
    [-32, 57, 16, 14, 9, 0.1],
  ],
  [
    [-37, -59, 23, 7.9, 8.2, 0.3],
    [-28, -62, 17, 5.4, 6.7, -0.3],
    [33, -62, 19, 8.6, 9, -0.6],
    [43, -53, 16, 8.3, 9.4, 0.4],
    [-47, -2, 21, 9, 15, 0.1],
    [47, 17, 24, 9, 13, -0.6],
    [27, 57, 22, 17, 8, 0.1],
    [-22, 54, 28, 11, 12, -0.9],
  ],
  [
    [-44, -39, 25, 12, 10, -0.8],
    [-33, -56, 30, 10, 12, 0.5],
    [38, -47, 32, 12, 11, -0.2],
    [24, -61, 19, 9, 10, 0.7],
    [-46, 14, 24, 9, 15, 0.1],
    [44, 23, 20, 12, 12, -0.4],
    [23, 62, 30, 14, 9, 0.6],
    [-25, 53, 21, 16, 10, 0.4],
  ],
];

function random(seed: number) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}

// Closed-in-plan limestone spurs. The angular strata run through several
// elevations, so a cliff has continuous gullies breaking an uneven cap.
function crag(spur: Spur, seed: number, trees: T.Vector3[], summit: T.Vector3) {
  const [x, z, height, width, depth, yaw] = spur;
  const rng = random(seed),
    phase = rng() * 6.28;
  const positions: number[] = [],
    uv: number[] = [],
    colors: number[] = [],
    indices: number[] = [];
  const around = 72,
    rows = 28;
  const moss = new T.Color(0x5e735f),
    limestone = new T.Color(0xe1e9e4);
  const color = new T.Color();
  const profile = [
    [0, 1.17],
    [0.15, 1.04],
    [0.31, 0.87],
    [0.55, 0.83],
    [0.68, 0.7],
    [0.83, 0.65],
    [0.9, 0.62],
    [0.96, 0.5],
    [1, 0.41],
  ];
  for (let row = 0; row <= rows; row++) {
    const t = row / rows;
    const hi = profile.findIndex(([h]) => h >= t);
    const [t0, r0] = profile[Math.max(0, hi - 1)],
      [t1, r1] = profile[hi];
    const r = T.MathUtils.lerp(r0, r1, t1 === t0 ? 0 : (t - t0) / (t1 - t0));
    for (let col = 0; col <= around; col++) {
      const a = ((col % around) / around) * 2 * Math.PI;
      const fold =
        0.15 * Math.sin(5 * a + phase) +
        0.087 * Math.sin(9 * a + 1.3 * phase + 0.6 * t) -
        0.14 * Math.pow(0.5 + 0.5 * Math.cos(13 * a + phase + t), 5);
      const band =
        0.024 * Math.sin(45 * t + 2 * Math.sin(a + phase)) +
        0.012 * Math.sin(71 * t + 3 * a);
      const cx = Math.cos(a),
        cz = Math.sin(a);
      const rx =
        width *
          (r * (1 + fold) + band) *
          Math.sign(cx) *
          Math.pow(Math.abs(cx), 0.82) +
        width * 0.18 * t * t;
      const rz =
        depth *
          (r * (1 + fold) + band) *
          Math.sign(cz) *
          Math.pow(Math.abs(cz), 0.81) -
        depth * 0.11 * t;
      const crown =
        0.86 +
        0.09 * Math.cos(a + phase) +
        0.055 * Math.sin(3 * a + phase) +
        0.025 * Math.sin(7 * a);
      const px = x + rx * Math.cos(yaw) + rz * Math.sin(yaw);
      const pz = z - rx * Math.sin(yaw) + rz * Math.cos(yaw);
      const py = -2 + height * t * crown;
      positions.push(px, py, pz);
      uv.push(
        ((col / around) * Math.PI * (width + depth)) / 9.7 +
          0.035 * Math.sin(a * 4 + t * 5),
        py / 11.5 + 0.048 * Math.sin(3 * a + phase),
      );
      const cover = T.MathUtils.clamp(
        1.9 * (t - 0.66) + 0.25 * Math.sin(3 * a + phase) - 1.6 * fold,
        0,
        0.85,
      );
      color
        .copy(limestone)
        .lerp(moss, cover)
        .multiplyScalar(0.85 + fold + band);
      colors.push(color.r, color.g, color.b);
      if (col && row) {
        const i = row * (around + 1) + col,
          prev = i - around - 1;
        indices.push(prev - 1, i - 1, prev, prev, i - 1, i);
      }
      if (row === rows && col % 3 === 0 && col < around && rng() > 0.22)
        trees.push(new T.Vector3(px, py - 0.24, pz));
    }
  }
  const center = new T.Vector3();
  const cap = positions.length / 3,
    last = rows * (around + 1);
  for (let i = 0; i < around; i++)
    center.add(new T.Vector3().fromArray(positions, 3 * (last + i)));
  center.multiplyScalar(1 / around);
  center.y += height * 0.014;
  summit.copy(center);
  positions.push(center.x, center.y, center.z);
  colors.push(moss.r, moss.g, moss.b);
  uv.push(0.5, 0.5);
  for (let i = 0; i < around; i++) indices.push(last + i, cap, last + i + 1);
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.Float32BufferAttribute(positions, 3));
  g.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
  g.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
  g.setIndex(indices);
  g.computeVertexNormals();
  return g;
}

// Wind-trained limbs carry separate pads of needles. Keep a single geometry for
// every little crown so the entire summit treeline takes one draw.
function summitPines(sites: T.Vector3[], seed: number) {
  const rng = random(seed),
    xyz: number[] = [],
    rgb: number[] = [];
  const bark = new T.Color(0x51463a),
    canopy = new T.Color(0x374d45),
    shade = new T.Color();
  function tri(a: T.Vector3, b: T.Vector3, c: T.Vector3, color: T.Color) {
    xyz.push(...a.toArray(), ...b.toArray(), ...c.toArray());
    for (let i = 0; i < 3; i++) rgb.push(color.r, color.g, color.b);
  }
  for (const p of sites) {
    const h = 0.75 + rng() * 1.8,
      lean = (rng() - 0.45) * h * 0.48,
      scale = h * (0.21 + rng() * 0.12);
    const crown = (t: number) =>
      new T.Vector3(p.x + lean * t * t, p.y + h * t, p.z + h * 0.1 * t);
    function limb(a: T.Vector3, b: T.Vector3, r0: number, r1: number) {
      const axis = b.clone().sub(a).normalize();
      const x = new T.Vector3(1, 0, 0).cross(axis).normalize();
      const z = axis.clone().cross(x);
      const rim = (origin: T.Vector3, r: number, angle: number) =>
        origin
          .clone()
          .addScaledVector(x, r * Math.cos(angle))
          .addScaledVector(z, r * Math.sin(angle));
      for (let k = 0; k < 4; k++) {
        const t = (k * Math.PI) / 2,
          u = t + Math.PI / 2;
        const lo = rim(a, r0, t),
          hi = rim(b, r1, t),
          next = rim(a, r0, u),
          top = rim(b, r1, u);
        tri(lo, next, hi, bark);
        tri(next, top, hi, bark);
      }
    }
    function tuft(center: T.Vector3, reach: number, twist: number) {
      const n = 8;
      const shape = Array.from({ length: n }, (_, j) => {
        const a = twist + (j * 2 * Math.PI) / n,
          r = reach * (0.7 + 0.37 * rng());
        return center
          .clone()
          .add(
            new T.Vector3(
              r * Math.cos(a),
              reach * (rng() - 0.5) * 0.23,
              r * Math.sin(a) * 0.77,
            ),
          );
      });
      const high = center.clone().add(new T.Vector3(0, reach * 0.42, 0));
      const low = center.clone().add(new T.Vector3(0, -reach * 0.19, 0));
      for (let j = 0; j < n; j++) {
        const a = shape[j],
          b = shape[(j + 1) % n];
        shade.copy(canopy).multiplyScalar(0.9 + 0.38 * rng());
        tri(b, a, high, shade);
        shade.multiplyScalar(0.72);
        tri(a, b, low, shade);
      }
    }
    limb(p, crown(0.57), h * 0.043, h * 0.029);
    limb(crown(0.57), crown(0.98), h * 0.029, h * 0.009);
    const azimuth = rng() * Math.PI * 2;
    for (let j = 0; j < 8; j++) {
      const t = 0.32 + 0.077 * j,
        angle = azimuth + j * 2.4 + 0.23 * rng();
      const length = scale * (1.45 - 0.075 * j) * (0.72 + 0.42 * rng());
      const start = crown(t),
        bend = start
          .clone()
          .add(
            new T.Vector3(
              length * 0.53 * Math.cos(angle),
              -h * 0.047,
              length * 0.53 * Math.sin(angle),
            ),
          );
      const end = start
        .clone()
        .add(
          new T.Vector3(
            length * Math.cos(angle),
            h * (0.008 + 0.075 * rng()),
            length * Math.sin(angle),
          ),
        );
      limb(start, bend, h * 0.02, h * 0.014);
      limb(bend, end, h * 0.014, h * 0.006);
      tuft(end, scale * (0.49 + 0.21 * rng()), angle);
      if (j % 2 === 0)
        tuft(bend.clone().lerp(end, 0.19), scale * 0.39, angle + 1);
    }
    tuft(crown(0.95), scale * 0.53, azimuth);
  }
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.Float32BufferAttribute(xyz, 3));
  g.setAttribute("color", new T.Float32BufferAttribute(rgb, 3));
  g.computeVertexNormals();
  return g;
}

export function karstSpurs(encounter: number, map: T.Texture) {
  const group = new T.Group(),
    sites: T.Vector3[] = [];
  const summits = spurs[encounter].map(() => new T.Vector3());
  const geometry = spurs[encounter].map((s, i) =>
    crag(s, 1429 + 203 * i + 97 * encounter, sites, summits[i]),
  );
  if (encounter === 1) {
    const beacon = ridgePavilion();
    beacon.position.copy(summits[1]);
    beacon.position.y -= 0.28;
    beacon.rotation.y = 0.31;
    group.add(beacon);
  }
  const stone = new T.MeshStandardMaterial({
    map,
    bumpMap: map,
    bumpScale: 0.16,
    vertexColors: true,
    roughness: 0.94,
  });
  const forest = new T.MeshStandardMaterial({
    vertexColors: true,
    roughness: 1,
    side: T.DoubleSide,
  });
  // Mist pools below the spurs. The court fog remains dense at their feet;
  // higher exposed faces retain their limestone detail against the sky.
  for (const material of [stone, forest])
    material.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader.replace(
        "#include <fog_vertex>",
        `#include <fog_vertex>
        #ifdef USE_FOG
          vFogDepth *= mix(0.93, 0.53, smoothstep(2.0, 20.0, (modelMatrix*vec4(transformed,1.0)).y));
        #endif`,
      );
    };
  const cliffs = new T.Mesh(mergeGeometries(geometry), stone);
  geometry.forEach((g) => g.dispose());
  cliffs.name = "Limestone spurs";
  group.add(cliffs);
  const pines = new T.Mesh(summitPines(sites, 1906 + encounter), forest);
  pines.name = "Summit pines";
  group.add(pines);
  return group;
}
