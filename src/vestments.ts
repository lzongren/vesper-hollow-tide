import * as T from "three";
import { angleDiff, type Attack } from "./combat";
import type { GripKey } from "./pilgrim";

// Wrist in actor space, followed by the azimuth and elevation of the long haft.
export const bellGuard: GripKey = [0, -0.32, 2.13, 0.52, -0.52, 1.05];
const hold = (key: GripKey, time: number): GripKey => [
  time,
  key[1],
  key[2],
  key[3],
  key[4],
  key[5],
];
interface Stroke {
  lift: GripKey[];
  strike: GripKey[];
  settle: GripKey[];
}
function stroke(lift: GripKey, contact: GripKey, follow: GripKey): Stroke {
  // Damage can start on the first active tick. The lead-in already carries the
  // bell into the strike; the remaining active interval is its follow-through.
  return {
    lift: [bellGuard, hold(lift, 0.7), hold(lift, 0.78), hold(contact, 1)],
    strike: [hold(contact, 0), hold(follow, 0.78), hold(follow, 1)],
    settle: [hold(follow, 0), hold(follow, 0.18), hold(bellGuard, 1)],
  };
}
const sweep = stroke(
  [0, -0.92, 2.58, 0.08, -1.88, 0.35],
  [0, -0.29, 2.02, 0.86, -0.25, 0.04],
  [0, 0.39, 1.84, 0.65, 1.3, -0.2],
);
const toll = stroke(
  [0, -0.33, 3.38, 0.15, -0.54, 1.96],
  [0, -0.26, 1.73, 0.83, 0.02, -0.34],
  [0, -0.25, 1.44, 0.68, 0.03, -0.57],
);
const charge = stroke(
  [0, -0.62, 2.1, 0.02, -0.82, 0.43],
  [0, -0.34, 2.17, 0.82, -0.1, 0.02],
  [0, -0.22, 2.04, 0.93, 0.1, -0.12],
);
export function bellStroke(shape: Attack["shape"], state: string) {
  const motion = shape === "circle" ? toll : shape === "dash" ? charge : sweep;
  if (state === "windup") return motion.lift;
  if (state === "active") return motion.strike;
  if (state === "recover") return motion.settle;
}

/** Each transverse cloth band lags its pinned neighbour. Spring in actor space
 * so clockwise turns and lateral rolls displace the free hem in opposite directions. */
export class MantleMotion {
  private last?: [number, number, number];
  private offsets = new Float32Array(16);
  private speeds = new Float32Array(16);
  private geometry: T.BufferGeometry;
  private base: Float32Array;
  private band: Float32Array;

  constructor(mesh: T.Mesh) {
    this.geometry = mesh.geometry;
    const p = this.geometry.attributes.position;
    this.base = new Float32Array(p.array);
    this.band = Float32Array.from(
      { length: p.count },
      (_, i) => (1 - this.geometry.attributes.uv.getY(i)) * 7,
    );
    if (p instanceof T.BufferAttribute) p.setUsage(T.DynamicDrawUsage);
  }

  step(x: number, z: number, yaw: number, dt: number, t: number, roll: number) {
    const prev = this.last;
    this.last = [x, z, yaw];
    if (!prev || dt <= 0 || Math.hypot(x - prev[0], z - prev[1]) > 1.8) {
      this.offsets.fill(0);
      this.speeds.fill(0);
    } else {
      const dx = (x - prev[0]) / dt,
        dz = (z - prev[1]) / dt;
      const lateral = dx * Math.cos(yaw) - dz * Math.sin(yaw),
        forward = dz * Math.cos(yaw) + dx * Math.sin(yaw);
      const twist = T.MathUtils.clamp(angleDiff(yaw, prev[2]) / dt, -9, 9);
      const lagX = T.MathUtils.clamp(
        -0.048 * lateral + 0.024 * twist,
        -0.52,
        0.52,
      );
      const lagZ = T.MathUtils.clamp(
        -0.045 * forward - 0.24 * roll,
        -0.62,
        0.14,
      );
      const substeps = Math.ceil(Math.min(dt, 0.08) * 120),
        h = Math.min(dt, 0.08) / substeps;
      for (let step = 0; step < substeps; step++)
        for (let j = 1; j <= 7; j++)
          for (let axis = 0; axis < 2; axis++) {
            const k = j * 2 + axis;
            const target =
              this.offsets[k - 2] * 0.74 +
              ((axis === 0 ? lagX : lagZ) * j) / 15;
            this.speeds[k] +=
              ((target - this.offsets[k]) * 170 - this.speeds[k] * 16) * h;
            this.offsets[k] += this.speeds[k] * h;
          }
    }
    const p = this.geometry.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const depth = this.band[i],
        j = Math.floor(depth),
        k = 2 * j,
        next = Math.min(14, k + 2),
        f = depth - j;
      const sx = T.MathUtils.lerp(this.offsets[k], this.offsets[next], f);
      const sz = T.MathUtils.lerp(
        this.offsets[k + 1],
        this.offsets[next + 1],
        f,
      );
      const bx = this.base[i * 3],
        by = this.base[i * 3 + 1],
        bz = this.base[i * 3 + 2],
        u = depth / 7;
      const pleat =
        Math.sin(t * 3.2 + bx * 14 - u * 4) *
        (0.012 + 0.032 * Math.min(1, Math.abs(sx) + Math.abs(sz))) *
        u *
        u;
      p.setXYZ(
        i,
        bx + sx,
        by + Math.min(0.25, (sx * sx + sz * sz) * 0.65) + roll * 0.13 * u * u,
        bz + sz + pleat,
      );
    }
    p.needsUpdate = true;
    this.geometry.computeVertexNormals();
  }
}

/** Overlapping plates fan out from a rounded cap, leaving the elbow free. */
export function lamellarShoulder(
  side: number,
  bronze: T.Material,
  border: T.Material,
  lining: T.Material,
) {
  const shoulder = new T.Group();
  const cap = new T.Mesh(
    new T.SphereGeometry(1, 32, 18, 0, Math.PI * 2, 0, 1.5),
    bronze,
  );
  cap.scale.set(0.385, 0.3, 0.39);
  shoulder.add(cap);
  for (let row = 0; row < 4; row++) {
    const vertices: number[] = [],
      uvs: number[] = [],
      indices: number[] = [];
    const trimPoints: T.Vector3[] = [];
    for (let i = 0; i <= 32; i++) {
      const u = i / 32,
        angle = (u - 0.5) * 3.36;
      const edge = Math.cos(angle * 0.89),
        radius = 0.31 + row * 0.034;
      for (let j = 0; j <= 4; j++) {
        const v = j / 4,
          r = radius + 0.073 * v;
        const x = side * (Math.cos(angle) * r + 0.016 * row);
        const y =
          0.14 -
          0.13 * row -
          0.194 * v -
          0.09 * edge -
          0.048 * Math.sin(Math.PI * u * 3) ** 2 * v;
        const z = Math.sin(angle) * r;
        vertices.push(x, y, z);
        uvs.push(u, 1 - v);
        if (j === 4) trimPoints.push(new T.Vector3(x, y, z));
        if (i && j) {
          const b = i * 5 + j;
          if (side === 1) indices.push(b - 6, b - 1, b, b - 6, b, b - 5);
          else indices.push(b - 6, b, b - 1, b - 6, b - 5, b);
        }
      }
    }
    const geometry = new T.BufferGeometry();
    geometry.setAttribute(
      "position",
      new T.Float32BufferAttribute(vertices, 3),
    );
    geometry.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    const plate = new T.Mesh(geometry, bronze);
    shoulder.add(plate);
    shoulder.add(
      new T.Mesh(
        new T.TubeGeometry(
          new T.CatmullRomCurve3(trimPoints),
          32,
          0.012,
          6,
          false,
        ),
        border,
      ),
    );
    for (const k of [4, 12, 20, 28]) {
      const stud = new T.Mesh(new T.SphereGeometry(0.023, 9, 7), border);
      stud.position.copy(trimPoints[k]);
      stud.position.y += 0.072;
      shoulder.add(stud);
    }
  }
  const padding = new T.Mesh(new T.SphereGeometry(1, 20, 14), lining);
  padding.scale.set(0.3, 0.33, 0.3);
  padding.position.y = -0.13;
  shoulder.add(padding);
  shoulder.traverse((o) => {
    o.castShadow = o.receiveShadow = true;
  });
  return shoulder;
}
