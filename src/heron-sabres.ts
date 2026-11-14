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
  // Flat faces split at the ridge to give the bevel a moving linear highlight.
  const section = [
    [-0.042, 0],
    [-0.016, 0.023],
    [0.071, 0.011],
    [0.12, 0],
    [0.071, -0.011],
    [-0.016, -0.023],
    [-0.042, 0],
  ];
  const length = 1.17;
  for (let k = 0; k < section.length - 1; k++) {
    const base = verts.length / 3;
    for (let j = 0; j <= 32; j++) {
      const u = j / 32,
        w = 0.95 + 0.23 * Math.sin(u * Math.PI),
        tip = Math.min(1, (1 - u) * 3.65);
      const cx = shaftX + 0.018 * u + 0.225 * u * u * u;
      for (let face = 0; face <= 1; face++) {
        const [x, z] = section[k + face];
        verts.push(
          side * (cx + x * w * tip),
          0.182 + length * u,
          0.022 + z * tip,
        );
        uv.push((k + face) / 6, u);
        const faceTint = [0.43, 0.67, 0.83, 0.83, 0.67, 0.43][k];
        const tone =
          faceTint + 0.04 * face + 0.024 * Math.sin(35 * u + 0.55 * k);
        colors.push(tone * 0.94, tone, tone * 1.02);
      }
      if (j) {
        const a = base + 2 * j - 2;
        indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
      }
    }
  }
  const blade = new T.BufferGeometry();
  blade.setAttribute("position", new T.Float32BufferAttribute(verts, 3));
  blade.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
  blade.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
  blade.setIndex(side > 0 ? indices : indices.reverse());
  blade.computeVertexNormals();
  add(m.steel, blade);
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
