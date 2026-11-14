import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import type { GripKey } from "./pilgrim";
import type { Attack } from "./combat";

export type HandSide = "Right" | "Left";
type Position = readonly [number, number, number, number, number];
type Stroke = { windup: GripKey[]; active: GripKey[]; recover: GripKey[] };
const key = (t: number, p: Position): GripKey => [t, ...p];

export const heronGuards: Record<HandSide, GripKey> = {
  Right: [0, -0.43, 1.76, 0.34, -0.72, 0.48],
  Left: [0, 0.46, 1.64, 0.19, 1.26, -0.41],
};
// Wrist positions are in actor metres. Each action has a preparation, contact
// and follow-through. Adjacent states share a key on the combat clock.
function stroke(
  side: HandSide,
  gather: Position,
  contact: Position,
  finish: Position,
): Stroke {
  const guard = heronGuards[side];
  return {
    windup: [guard, key(0.58, gather), key(0.78, gather), key(1, contact)],
    active: [key(0, contact), key(0.77, finish), key(1, finish)],
    recover: [
      key(0, finish),
      key(0.14, finish),
      [1, guard[1], guard[2], guard[3], guard[4], guard[5]],
    ],
  };
}
const gestures = {
  sector: {
    Right: stroke(
      "Right",
      [-0.75, 2.33, 0.14, -1.65, 0.62],
      [-0.19, 1.99, 0.82, 0.02, 0.02],
      [0.32, 1.57, 0.4, 1.55, -0.3],
    ),
    Left: stroke(
      "Left",
      [0.12, 1.88, 0.46, -0.65, 0.82],
      [0.52, 2.17, 0.32, 1.32, 0.9],
      [0.6, 2.02, 0.19, 1.39, 0.7],
    ),
  },
  dash: {
    Right: stroke(
      "Right",
      [-0.43, 1.77, 0.06, -0.32, 0.14],
      [-0.22, 1.83, 0.86, 0.01, 0.04],
      [-0.23, 1.76, 0.86, 0.08, -0.06],
    ),
    Left: stroke(
      "Left",
      [0.43, 2.17, 0.08, 1.63, 0.8],
      [0.6, 2.12, 0.06, 1.82, 0.49],
      [0.56, 1.88, 0.1, 1.78, 0.27],
    ),
  },
  fan: {
    Right: stroke(
      "Right",
      [-0.12, 2.26, 0.47, 0.76, 0.96],
      [-0.66, 2.09, 0.48, -1.24, 0.48],
      [-0.77, 1.96, 0.3, -1.49, 0.25],
    ),
    Left: stroke(
      "Left",
      [0.1, 2.05, 0.54, -0.74, 0.82],
      [0.68, 2.07, 0.5, 1.23, 0.5],
      [0.77, 1.94, 0.34, 1.49, 0.28],
    ),
  },
};

export function heronStroke(
  shape: Attack["shape"] | undefined,
  phase: string,
  side: HandSide,
) {
  if (shape !== "fan" && shape !== "sector" && shape !== "dash") return;
  if (phase === "windup" || phase === "active" || phase === "recover")
    return gestures[shape][side][phase];
}

interface Finishes {
  skin: T.Material;
  steel: T.Material;
  bronze: T.Material;
  binding: T.Material;
}

/** Thumb crosses the index finger; the other digits wrap progressively lower
 * on an oval hilt. The hand, guard and blade all use the same wrist socket. */
export function duelistSabre(side: number, m: Finishes) {
  const socket = new T.Group(),
    parts = new Map<T.Material, T.BufferGeometry[]>();
  function add(material: T.Material, g: T.BufferGeometry) {
    const flat = g.index ? g.toNonIndexed() : g;
    if (flat !== g) g.dispose();
    if (!parts.has(material)) parts.set(material, []);
    parts.get(material)!.push(flat);
  }
  function ellipsoid(
    material: T.Material,
    x: number,
    y: number,
    z: number,
    rx: number,
    ry: number,
    rz: number,
    angle = 0,
  ) {
    add(
      material,
      new T.SphereGeometry(1, 14, 10)
        .scale(rx, ry, rz)
        .rotateZ(angle)
        .translate(side * x, y, z),
    );
  }
  function cord(material: T.Material, pts: number[][], radius: number) {
    const path = new T.CatmullRomCurve3(
      pts.map(([x, y, z]) => new T.Vector3(side * x, y, z)),
    );
    add(
      material,
      new T.TubeGeometry(path, Math.max(12, pts.length * 3), radius, 8, false),
    );
  }
  const shaftX = 0.042;
  add(
    m.binding,
    new T.CylinderGeometry(0.033, 0.038, 0.295, 16)
      .scale(1, 1, 0.81)
      .translate(side * shaftX, 0.012, 0.022),
  );
  const wrap = Array.from({ length: 64 }, (_, i) => {
    const t = i / 63,
      a = t * Math.PI * 15;
    return [
      shaftX + 0.036 * Math.cos(a),
      -0.122 + 0.267 * t,
      0.022 + 0.029 * Math.sin(a),
    ];
  });
  cord(m.bronze, wrap, 0.004);
  ellipsoid(m.bronze, shaftX, -0.151, 0.022, 0.057, 0.04, 0.043);
  ellipsoid(m.skin, -0.02, 0.003, -0.011, 0.058, 0.089, 0.04, -0.11 * side);
  for (let j = 0; j < 4; j++) {
    const y = 0.065 - j * 0.037,
      r = 0.019 - j * 0.0014;
    const zs = 0.005 + j * 0.002;
    cord(
      m.skin,
      [
        [0.002, y, -0.022],
        [0.044, y + 0.006, -0.021],
        [0.082, y - 0.002, zs],
        [0.079, y - 0.014, 0.049],
        [0.048, y - 0.02, 0.06],
        [0.028 + j * 0.003, y - 0.018, 0.055],
      ],
      r,
    );
    ellipsoid(
      m.skin,
      0.028 + j * 0.003,
      y - 0.018,
      0.055,
      r,
      r * 0.92,
      r * 0.9,
    );
    ellipsoid(m.skin, 0.055, y + 0.006, -0.017, r * 1.17, r * 0.92, r * 0.9);
  }
  cord(
    m.skin,
    [
      [-0.05, 0.024, -0.009],
      [-0.046, 0.067, 0.01],
      [-0.029, 0.081, 0.046],
      [0.015, 0.059, 0.076],
      [0.043, 0.044, 0.065],
    ],
    0.024,
  );
  ellipsoid(m.skin, 0.043, 0.044, 0.065, 0.024, 0.021, 0.021);
  const guard = new T.Shape();
  guard.moveTo(-0.17, 0);
  guard.bezierCurveTo(-0.12, -0.042, -0.06, -0.015, 0, -0.012);
  guard.bezierCurveTo(0.064, -0.018, 0.135, -0.037, 0.19, 0.074);
  guard.bezierCurveTo(0.12, 0.035, 0.093, 0.046, 0.041, 0.041);
  guard.bezierCurveTo(-0.015, 0.06, -0.1, 0.034, -0.17, 0);
  const bar = new T.ExtrudeGeometry(guard, {
    depth: 0.039,
    bevelSize: 0.008,
    bevelThickness: 0.008,
    bevelSegments: 2,
    curveSegments: 12,
  });
  if (side < 0) bar.rotateY(Math.PI);
  add(m.bronze, bar.translate(side * shaftX, 0.153, 0.022 - side * 0.0195));
  const verts: number[] = [],
    indices: number[] = [],
    colors: number[] = [],
    uv: number[] = [];
  // A recessed fuller interrupts the broad face. The last quarter of the
  // width is ground to the edge. Each change of slope has its own normals.
  const profile = [
    [-0.042, 0, 0.28], [-0.031, 0.021, 0.58], [-0.016, 0.024, 0.63],
    [-0.009, 0.015, 0.21], [0.009, 0.014, 0.20], [0.016, 0.023, 0.58],
    [0.072, 0.014, 0.55], [0.12, 0, 1.00],
  ];
  function surface(t: number, x: number, z: number) {
    const tip = Math.min(1, (1 - t) * 3.65);
    const width = (0.95 + 0.23 * Math.sin(t * Math.PI)) * tip;
    return [
      side * (shaftX + 0.018 * t + 0.225 * t ** 3 + x * width),
      0.182 + 1.17 * t,
      0.022 + z * tip,
    ];
  }
  for (const front of [-1, 1]) {
    for (let k = 0; k < profile.length - 1; k++) {
      const base = verts.length / 3;
      const [x0, z0, c0] = profile[k], [x1, z1, c1] = profile[k + 1];
      for (let j = 0; j <= 64; j++) {
        const t = j / 64;
        for (let h = 0; h <= 8; h++) {
          const q = h / 8;
          const x = T.MathUtils.lerp(x0, x1, q);
          verts.push(...surface(t, x, front * T.MathUtils.lerp(z0, z1, q)));
          uv.push((x + 0.042) / 0.162, t);
          // Irregular bright temper line at the transition to the ground edge.
          const wave = 0.073 + 0.004 * Math.sin(37*t) + 0.0025 * Math.sin(61*t);
          const line = Math.exp(-((x-wave)**2) / 0.000023);
          const grain = Math.sin(150*x + 4*Math.sin(11*t) + 9*t);
          const tone = T.MathUtils.lerp(c0, c1, q) + 0.22*line + 0.026*grain;
          colors.push(tone * 0.92, tone * 0.965, tone);
          if (j && h) {
            const d = base + j*9 + h, a = d-10, b = d-9, c = d-1;
            if (front * side > 0) indices.push(a,b,c,b,d,c);
            else indices.push(a,c,b,b,c,d);
          }
        }
      }
    }
  }
  const blade = new T.BufferGeometry();
  blade.setAttribute("position", new T.Float32BufferAttribute(verts, 3));
  blade.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
  blade.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
  blade.setIndex(indices);
  blade.computeVertexNormals();
  add(m.steel, blade);
  // Fine brass wire let into both flats. Each vane returns to the central
  // quill. Its z coordinate follows the ground face all the way to its tip.
  for (const front of [-1, 1]) {
    const inlay = (t: number, x: number) => {
      const z = T.MathUtils.lerp(0.023, 0.014, (x-0.016)/0.056);
      const [px, py, pz] = surface(t, x, front*(z+0.0009));
      return [px*side, py, pz];
    };
    const quill = (t: number) => 0.032 + 0.011 * Math.sin(7*t);
    const points = Array.from({length: 18}, (_, i) => {
      const t = 0.045 + 0.36*i/17;
      return inlay(t, quill(t));
    });
    cord(m.bronze, points, 0.0018);
    for (let i = 0; i < 5; i++) {
      const start = 0.06 + i*0.056;
      for (const direction of [-1, 1]) {
        const reach = (1-i*0.105) * (direction < 0 ? 0.016 : 0.026);
        cord(m.bronze, [
          inlay(start, quill(start)),
          inlay(start+0.025, quill(start)+direction*reach*0.74),
          inlay(start+0.069, quill(start)+direction*reach),
        ], 0.0015);
      }
    }
  }
  for (const z of [-0.026, 0.026]) {
    cord(
      m.bronze,
      [
        [shaftX - 0.006, 0.185, 0.022 + z],
        [shaftX + 0.014, 0.222, 0.022 + z],
        [shaftX + 0.006, 0.257, 0.022 + z],
      ],
      0.005,
    );
  }
  for (const [material, geos] of parts) {
    const mesh = new T.Mesh(mergeGeometries(geos), material);
    mesh.castShadow = mesh.receiveShadow = true;
    socket.add(mesh);
    geos.forEach((g) => g.dispose());
  }
  return socket;
}
