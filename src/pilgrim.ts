import * as T from "three";
import { jianPoint } from "./pilgrim-jian";

// Keys describe the wrist and the blade direction in the actor's metre-scale frame.
// The two contact keys coincide with the combat simulation at 0.14 s and 0.46 s.
export type GripKey = readonly [
  time: number,
  x: number,
  y: number,
  z: number,
  yaw: number,
  elevation: number,
];
const guard: GripKey = [0, -0.34, 1.1, 0.24, -0.52, 0.52];
const returnGuard: GripKey = [
  1,
  guard[1],
  guard[2],
  guard[3],
  guard[4],
  guard[5],
];
const cuts: Record<string, GripKey[]> = {
  light: [
    guard,
    [0.19, -0.52, 1.36, 0.2, -1.54, 0.61],
    [0.326, -0.29, 1.32, 0.46, -0.14, 0.17],
    [0.53, 0.12, 1.12, 0.37, 1.4, -0.18],
    [0.74, 0.04, 1.04, 0.3, 1.14, -0.23],
    returnGuard,
  ],
  heavy: [
    guard,
    [0.28, -0.35, 1.81, 0.05, -1.81, 1.15],
    [0.4, -0.32, 1.82, 0.09, -1.72, 1.15],
    [0.523, -0.2, 1.35, 0.47, -0.09, 0.18],
    [0.68, 0.04, 0.99, 0.25, 0.86, -0.75],
    [0.8, -0.01, 0.96, 0.27, 0.68, -0.67],
    returnGuard,
  ],
  parry: [
    guard,
    [0.22, -0.05, 1.43, 0.4, -1.12, 0.7],
    [0.53, -0.05, 1.46, 0.4, -1.16, 0.69],
    returnGuard,
  ],
};
const direction = new T.Vector3(),
  desired = new T.Vector3(),
  actual = new T.Vector3();
const shoulder = new T.Vector3(),
  elbow = new T.Vector3(),
  wrist = new T.Vector3(),
  pole = new T.Vector3();
const worldQ = new T.Quaternion(),
  parentQ = new T.Quaternion(),
  correction = new T.Quaternion();
const bladeFrame = new T.Quaternion(),
  desiredHand = new T.Quaternion();
const grip = new T.Vector3(),
  blade = new T.Vector3();
const up = new T.Vector3(0, 1, 0);

function aimBone(bone: T.Bone, end: T.Bone, destination: T.Vector3) {
  const origin = bone.getWorldPosition(actual);
  desired.copy(destination).sub(origin).normalize();
  end.getWorldPosition(direction).sub(origin).normalize();
  correction.setFromUnitVectors(direction, desired);
  bone.getWorldQuaternion(worldQ).premultiply(correction);
  bone.parent!.getWorldQuaternion(parentQ).invert();
  bone.quaternion.copy(parentQ.multiply(worldQ));
  bone.updateWorldMatrix(false, true);
}

export class WeaponGrip {
  private socketRotation: T.Quaternion;
  constructor(
    private root: T.Group,
    private upper: T.Bone,
    private fore: T.Bone,
    private hand: T.Bone,
    weapon: T.Group,
    private rest: GripKey = guard,
    private support?: readonly [T.Bone, T.Bone, T.Bone],
    private side = -1,
  ) {
    // Object3D.attach compensates for the source armature's centimetre units.
    this.hand.getWorldPosition(weapon.position);
    this.root.worldToLocal(weapon.position);
    weapon.quaternion.setFromUnitVectors(
      up,
      blade.set(-0.38, 0.51, 0.77).normalize(),
    );
    this.hand.attach(weapon);
    this.socketRotation = weapon.quaternion.clone().invert();
  }
  pose(action: string, progress: number) {
    this.poseKeys(cuts[action], progress);
  }
  poseKeys(keys: readonly GripKey[] | undefined, progress: number) {
    let a = this.rest,
      b = this.rest,
      f = 0;
    if (keys) {
      const time = T.MathUtils.clamp(progress, 0, 1);
      const hi = keys.findIndex((key) => key[0] >= time);
      b = keys[hi < 0 ? keys.length - 1 : hi];
      a = keys[Math.max(0, (hi < 0 ? keys.length - 1 : hi) - 1)];
      if (b[0] > a[0]) {
        f = (time - a[0]) / (b[0] - a[0]);
        f = f * f * (3 - 2 * f);
      }
    }
    const value = (i: number) => T.MathUtils.lerp(a[i], b[i], f);
    grip.set(value(1), value(2), value(3));
    this.root.localToWorld(grip);
    solveArm(this.root, this.upper, this.fore, this.hand, grip, this.side);
    const yaw = value(4),
      pitch = value(5);
    blade.set(
      Math.sin(yaw) * Math.cos(pitch),
      Math.sin(pitch),
      Math.cos(yaw) * Math.cos(pitch),
    );
    bladeFrame.setFromUnitVectors(up, blade);
    this.root
      .getWorldQuaternion(desiredHand)
      .multiply(bladeFrame)
      .multiply(this.socketRotation);
    this.fore.getWorldQuaternion(parentQ).invert();
    this.hand.quaternion.copy(parentQ.multiply(desiredHand));

    if (this.support) {
      // The support palm rides the haft below the driving hand.
      this.hand.getWorldPosition(grip);
      this.root.getWorldQuaternion(worldQ);
      grip.addScaledVector(blade.applyQuaternion(worldQ), -0.43);
      solveArm(this.root, ...this.support, grip, 1);
    }
  }
}
function solveArm(
  root: T.Group,
  upper: T.Bone,
  fore: T.Bone,
  hand: T.Bone,
  target: T.Vector3,
  side: number,
) {
  upper.getWorldPosition(shoulder);
  root.localToWorld(pole.set(side, shoulder.y - root.position.y - 0.25, -0.32));
  solveTwoBone(upper, fore, hand, target, pole);
}

export function solveTwoBone(
  upper: T.Bone,
  fore: T.Bone,
  hand: T.Bone,
  target: T.Vector3,
  bendPoint: T.Vector3,
) {
  upper.getWorldPosition(shoulder);
  fore.getWorldPosition(elbow);
  hand.getWorldPosition(wrist);
  const upperLength = shoulder.distanceTo(elbow),
    lowerLength = elbow.distanceTo(wrist);
  const axis = desired.copy(target).sub(shoulder).normalize();
  const d = T.MathUtils.clamp(
    shoulder.distanceTo(target),
    Math.abs(upperLength - lowerLength) + 0.001,
    upperLength + lowerLength - 0.001,
  );
  const along = (upperLength ** 2 - lowerLength ** 2 + d ** 2) / (2 * d);
  const offset = Math.sqrt(Math.max(0, upperLength ** 2 - along ** 2));
  pole.copy(bendPoint).sub(shoulder);
  pole.addScaledVector(axis, -pole.dot(axis)).normalize();
  elbow
    .copy(shoulder)
    .addScaledVector(axis, along)
    .addScaledVector(pole, offset);
  wrist.copy(shoulder).addScaledVector(axis, d);
  aimBone(upper, fore, elbow);
  aimBone(fore, hand, wrist);
}

export function mantleGeometry() {
  const geometry = new T.PlaneGeometry(1, 1, 56, 52),
    points = geometry.attributes.position;
  for (let i = 0; i < points.count; i++) {
    const u = points.getX(i) * 2,
      drop = 0.5 - points.getY(i),
      edge = Math.abs(u);
    const folds = Math.sin(u * 13 + drop * 0.7) * (0.025 + 0.055 * drop);
    points.setXYZ(
      i,
      Math.sin(u * 1.68) * (0.36 + 0.18 * drop),
      0.52 - drop * (1.22 - 0.19 * edge ** 3) + 0.024 * Math.cos(u * 15) * drop,
      -0.19 * Math.cos(u * 1.68) - 0.07 - 0.21 * drop + folds,
    );
  }
  geometry.computeVertexNormals();
  return geometry;
}

/** Short exposure at the moving point. Timestamped samples decay in seconds
 * so the wake has the same lifetime at different presentation rates. */
export class BladeTrail extends T.Mesh<T.BufferGeometry, T.MeshBasicMaterial> {
  private static readonly count = 16;
  private static readonly lifetime = 0.05;
  private samples = 0;
  private lastProgress = 0;
  private lastAction = "";
  private times = new Float64Array(BladeTrail.count);
  private positions = new Float32Array(BladeTrail.count * 6);
  private colors = new Float32Array(BladeTrail.count * 8);

  constructor() {
    const geometry = new T.BufferGeometry();
    const material = new T.MeshBasicMaterial({
      color: 0xb7c7c5,
      side: T.DoubleSide,
      vertexColors: true,
      transparent: true,
      opacity: 0.28,
      depthWrite: false,
      forceSinglePass: true,
    });
    super(geometry, material);
    this.colors.fill(1);
    geometry.setAttribute(
      "position",
      new T.BufferAttribute(this.positions, 3).setUsage(T.DynamicDrawUsage),
    );
    geometry.setAttribute(
      "color",
      new T.BufferAttribute(this.colors, 4).setUsage(T.DynamicDrawUsage),
    );
    const indices: number[] = [];
    for (let i = 0; i < BladeTrail.count - 1; i++) {
      const a = i * 2;
      indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
    geometry.setIndex(indices);
    geometry.setDrawRange(0, 0);
    this.frustumCulled = false;
    this.visible = false;
  }

  sample(weapon: T.Group, action: string, progress: number, now: number) {
    const cutting =
      action === "light"
        ? progress > 0.2 && progress < 0.56
        : action === "heavy" && progress > 0.39 && progress < 0.7;
    if (
      !cutting ||
      action !== this.lastAction ||
      progress < this.lastProgress ||
      now < this.times[0]
    )
      this.samples = 0;
    this.lastAction = action;
    this.lastProgress = progress;
    while (
      this.samples &&
      now - this.times[this.samples - 1] >= BladeTrail.lifetime
    )
      this.samples--;
    if (cutting && (!this.samples || now > this.times[0])) {
      // Leave the strong part of the blade visible. Only the last twelve
      // centimetres sweep a feathered mark in the air.
      weapon.localToWorld(grip.set(0, jianPoint - 0.12, 0));
      weapon.localToWorld(blade.set(0, jianPoint - 0.015, 0));
      const speed = this.samples
        ? Math.hypot(
            blade.x - this.positions[3],
            blade.y - this.positions[4],
            blade.z - this.positions[5],
          ) /
          (now - this.times[0])
        : 0;
      this.positions.copyWithin(6, 0, this.positions.length - 6);
      this.times.copyWithin(1, 0, BladeTrail.count - 1);
      this.times[0] = now;
      grip.toArray(this.positions, 0);
      blade.toArray(this.positions, 3);
      this.samples = Math.min(BladeTrail.count, this.samples + 1);
      this.material.opacity = 0.27 * T.MathUtils.smoothstep(speed, 2.8, 13);
      for (let i = 0; i < this.samples; i++) {
        const freshness = 1 - (now - this.times[i]) / BladeTrail.lifetime;
        this.colors[i * 8 + 3] = 0;
        this.colors[i * 8 + 7] = freshness * freshness;
      }
      this.geometry.attributes.position.needsUpdate = true;
      this.geometry.attributes.color.needsUpdate = true;
    }
    this.visible = this.samples > 1 && this.material.opacity > 0;
    this.geometry.setDrawRange(0, Math.max(0, this.samples - 1) * 6);
  }
}
