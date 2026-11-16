import * as T from "three";
import type { Hazard } from "./combat";
import { solveTwoBone } from "./pilgrim";

type CastPose = readonly [time: number, x: number, y: number, z: number, pitch: number, roll: number];
const gesture: CastPose[] = [
  [0, 1.01, 2.83, .52, 0, 0],
  [.37, .48, 3.02, .36, -.32, .20],
  [.83, .84, 3.77, .26, -.98, -.42],
  [1, .86, 3.80, .27, -1.04, -.45],
  [1.19, 1.16, 3.36, .38, -.56, -.76],
  [1.72, 1.10, 3.40, .46, -.67, -.64],
  [2.06, 1.25, 3.51, .26, -.80, -.74],
  [2.28, 1.36, 2.98, .38, .06, -.14],
  [2.54, 1.22, 2.90, .40, .18, -.13],
  [3, 1.01, 2.83, .52, 0, 0],
];

/** The first vent is the mark left at the pilgrim's feet. Its delay can
 * outlast recovery in the awakened phase. Keep the seal in time with it. */
export function sealTime(state: string, eruption: boolean, progress: number, hazards: readonly Hazard[]) {
  if (state === "dead" || state === "stagger" || state === "phase") return 0;
  if (eruption && state === "windup") return T.MathUtils.clamp(progress, 0, 1);
  const mark = hazards.find(h => h.type === "eruption" && h.targeted);
  if (!mark) return 0;
  return mark.age <= mark.delay ? 1 + mark.age / mark.delay * 1.06 :
    2.06 + (mark.age - mark.delay) / (mark.life - mark.delay) * .94;
}

export function castFingers(time: number) {
  const closing = T.MathUtils.smoothstep(time, 2.06, 2.27);
  return {
    open: T.MathUtils.smoothstep(time, .18, .88) * (1 - closing),
    closed: closing * (1 - T.MathUtils.smoothstep(time, 2.54, 3)),
  };
}

export class CinderCast {
  private target = new T.Vector3();
  private bend = new T.Vector3();
  private base = new T.Quaternion();
  private frame = new T.Quaternion();
  private rotation = new T.Quaternion();
  private angles = new T.Euler();
  private weight = 0;

  constructor(private root: T.Group, private upper: T.Bone, private fore: T.Bone, private hand: T.Bone) {}

  pose(time: number, dt: number) {
    const t = T.MathUtils.clamp(time, 0, 3);
    const amount = T.MathUtils.smoothstep(t, 0, .28) * (1 - T.MathUtils.smoothstep(t, 2.54, 3));
    this.weight = T.MathUtils.damp(this.weight, amount, 23, dt);
    if (this.weight < .001) return;

    const hi = Math.max(1, gesture.findIndex(key => key[0] >= t));
    const a = gesture[hi - 1], b = gesture[hi];
    const u = T.MathUtils.smoothstep(t, a[0], b[0]);
    const at = (i: number) => T.MathUtils.lerp(a[i], b[i], u);
    this.hand.getWorldQuaternion(this.base);
    this.root.worldToLocal(this.hand.getWorldPosition(this.target));
    this.target.lerp(this.bend.set(at(1), at(2), at(3)), this.weight);
    this.root.localToWorld(this.target);
    this.root.localToWorld(this.bend.set(1.58, 2.81, -.48));
    solveTwoBone(this.upper, this.fore, this.hand, this.target, this.bend);

    // Rotate the palm about actor axes after solving the bones. The original
    // wrist basis preserves finger direction through turns and hit reactions.
    this.root.getWorldQuaternion(this.frame);
    this.rotation.setFromEuler(this.angles.set(at(4)*this.weight, 0, at(5)*this.weight));
    this.rotation.premultiply(this.frame).multiply(this.frame.invert()).multiply(this.base);
    this.hand.parent!.getWorldQuaternion(this.frame).invert();
    this.hand.quaternion.copy(this.frame.multiply(this.rotation));
    this.hand.updateWorldMatrix(false, true);
  }
}
