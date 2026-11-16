import * as T from "three";
import { solveTwoBone } from "./pilgrim";

const upAxis = new T.Vector3(0, 1, 0);
const rightAxis = new T.Vector3(1, 0, 0);

class Leg {
  readonly rest = new T.Vector3();
  readonly sole = new T.Quaternion();
  readonly target = new T.Vector3();
  readonly neutral = new T.Vector3();

  constructor(
    readonly hip: T.Bone,
    readonly knee: T.Bone,
    readonly ankle: T.Bone,
    root: T.Group,
  ) {
    root.worldToLocal(ankle.getWorldPosition(this.rest));
    root
      .getWorldQuaternion(this.sole)
      .invert()
      .multiply(ankle.getWorldQuaternion(new T.Quaternion()));
  }
}

/** Court coordinates stay fixed under the supporting foot while the opposite knee swings. */
export class Footwork {
  private readonly legs: Leg[];
  private readonly previous = new T.Vector3();
  private readonly velocity = new T.Vector3();
  private readonly start = new T.Vector3();
  private readonly end = new T.Vector3();
  private readonly pole = new T.Vector3();
  private readonly parent = new T.Quaternion();
  private readonly pitch = new T.Quaternion();
  private readonly yaw = new T.Quaternion();
  private initialized = false;
  private swing = -1;
  private evadeProgress = -1;
  private next = 0;
  private progress = 0;
  private duration = 0.2;

  constructor(
    private root: T.Group,
    bones: Map<string, T.Bone>,
    private height: number,
  ) {
    this.legs = ["Left", "Right"].map(
      (side) =>
        new Leg(
          bones.get(side + "UpLeg")!,
          bones.get(side + "Leg")!,
          bones.get(side + "Foot")!,
          root,
        ),
    );
  }

  reset() {
    this.evadeProgress = -1;
    this.initialized = false;
    this.swing = -1;
    this.progress = 0;
  }

  /** The combat dash stops translating at 0.32 s. Land on the leading foot
   * near that instant and draw the trailing boot underneath during recovery. */
  evade(progress: number, direction: { x: number; z: number }) {
    const root = this.root,
      h = this.height;
    const t = T.MathUtils.clamp(progress, 0, 1);
    const sweep = Math.sin(Math.PI * t);
    const rise = Math.sin(Math.PI * T.MathUtils.clamp((t - 0.06) / 0.6, 0, 1));
    const absorb = Math.sin(
      Math.PI * T.MathUtils.clamp((t - 0.62) / 0.38, 0, 1),
    );
    const yaw = root.rotation.y;
    const side = Math.cos(yaw) * direction.x - Math.sin(yaw) * direction.z;
    const forward = Math.sin(yaw) * direction.x + Math.cos(yaw) * direction.z;
    const lead =
      Math.abs(side) > 0.32
        ? this.legs[0].rest.x * side > 0
          ? 0
          : 1
        : forward >= 0
          ? 0
          : 1;
    const reach =
      T.MathUtils.smoothstep(t, 0.08, 0.59) *
      (1 - T.MathUtils.smoothstep(t, 0.68, 1));
    root.position.y =
      h * (-0.065 - 0.12 * sweep + 0.075 * rise - 0.06 * absorb);
    root.rotation.x = forward * (0.43 * rise - 0.16 * absorb);
    root.rotation.z = -side * (0.46 * rise - 0.15 * absorb);
    root.updateWorldMatrix(true, false);
    this.yaw.setFromAxisAngle(upAxis, yaw);
    for (const [index, leg] of this.legs.entries()) {
      const leading = index === lead;
      const stride = leading ? 0.26 * reach : -0.24 * sweep;
      const lift = leading
        ? 0.14 * rise
        : 0.245 *
          Math.sin(Math.PI * T.MathUtils.clamp((t - 0.12) / 0.8, 0, 1)) ** 2;
      leg.target.copy(leg.rest).applyQuaternion(this.yaw);
      leg.target.x += root.position.x + direction.x * h * stride;
      leg.target.z += root.position.z + direction.z * h * stride;
      leg.target.y += h * lift;
      this.plant(leg, leading ? -0.24 * rise : 0.56 * sweep);
    }
    const landed = t >= 0.66 && this.evadeProgress < 0.66;
    this.evadeProgress = t;
    this.previous.copy(root.position);
    this.initialized = false;
    this.swing = -1;
    return landed ? this.legs[lead].target : undefined;
  }

  private plant(leg: Leg, pitch: number) {
    const h = this.height;
    this.pole.set(leg.rest.x * 1.24, h * 0.35, h * 0.48);
    this.root.localToWorld(this.pole);
    solveTwoBone(leg.hip, leg.knee, leg.ankle, leg.target, this.pole);
    leg.knee.getWorldQuaternion(this.parent).invert();
    leg.ankle.quaternion.copy(this.parent).multiply(this.yaw);
    if (pitch)
      leg.ankle.quaternion.multiply(
        this.pitch.setFromAxisAngle(rightAxis, pitch),
      );
    leg.ankle.quaternion.multiply(leg.sole);
  }

  pose(dt: number): T.Vector3 | undefined {
    this.evadeProgress = -1;
    const root = this.root,
      h = this.height;
    this.velocity.set(
      root.position.x - this.previous.x,
      0,
      root.position.z - this.previous.z,
    );
    this.previous.copy(root.position);
    if (this.velocity.length() > h * 0.66) this.reset();
    this.velocity
      .multiplyScalar(1 / Math.max(1 / 240, dt))
      .clampLength(0, h * 2.5);
    root.getWorldQuaternion(this.yaw);
    for (const leg of this.legs) {
      leg.neutral.copy(leg.rest).applyQuaternion(this.yaw);
      leg.neutral.x += root.position.x;
      leg.neutral.z += root.position.z;
      if (!this.initialized) leg.target.copy(leg.neutral);
    }
    if (!this.initialized) this.velocity.set(0, 0, 0);
    this.initialized = true;
    if (this.swing < 0) {
      const other = 1 - this.next;
      const error = (index: number) =>
        this.legs[index].target.distanceTo(this.legs[index].neutral);
      const threshold = h * (this.velocity.lengthSq() > 0.01 ? 0.068 : 0.042);
      const index = error(this.next) > threshold ? this.next : other;
      if (error(index) > threshold) {
        this.swing = index;
        this.next = 1 - index;
        this.progress = 0;
        this.duration = T.MathUtils.clamp(
          0.29 - (this.velocity.length() / h) * 0.08,
          0.12,
          0.27,
        );
        this.start.copy(this.legs[index].target);
        this.end
          .copy(this.legs[index].neutral)
          .addScaledVector(this.velocity, this.duration * 1.25);
      }
    }
    let landed: T.Vector3 | undefined;
    if (this.swing >= 0) {
      const leg = this.legs[this.swing];
      this.progress = Math.min(1, this.progress + dt / this.duration);
      const t = this.progress,
        arch = 4 * t * (1 - t);
      leg.target.lerpVectors(this.start, this.end, t * t * (3 - 2 * t));
      leg.target.y +=
        arch * Math.min(h * 0.082, this.start.distanceTo(this.end) * 0.3);
      if (t === 1) {
        landed = leg.target;
        this.swing = -1;
      }
    }
    // Flex the hips to leave extension available during the support phase.
    root.position.y -=
      h *
      (0.065 +
        (this.swing >= 0 ? 0.012 * Math.sin(Math.PI * this.progress) : 0));
    root.updateWorldMatrix(true, false);
    for (const leg of this.legs) this.plant(leg, 0);
    return landed;
  }
}
