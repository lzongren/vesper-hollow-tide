/** Export both hands, their fittings and the wrist-relative stroke animation. */
import * as T from "three";
import { duelistSabre, heronStroke } from "../src/heron-sabres";
import { BOSSES } from "../src/combat";
import { bake } from "./bake_glb";

const materials = {
  skin: new T.MeshStandardMaterial({
    name: "Ivory hand",
    color: 0xe0d2b2,
    metalness: 0.13,
    roughness: 0.39,
  }),
  binding: new T.MeshStandardMaterial({
    name: "Hilt binding",
    color: 0x557675,
    metalness: 0.52,
    roughness: 0.32,
  }),
  steel: new T.MeshStandardMaterial({
    name: "Honed steel",
    color: 0xe7f1ed,
    vertexColors: true,
    metalness: 0.6,
    roughness: 0.25,
  }),
  bronze: new T.MeshStandardMaterial({
    name: "Bronze fittings",
    color: 0xb1935c,
    metalness: 0.72,
    roughness: 0.45,
  }),
};
const pair = new T.Group(),
  up = new T.Vector3(0, 1, 0);
const hands = ["Right", "Left"] as const;
for (const hand of hands) {
  const socket = duelistSabre(hand === "Left" ? 1 : -1, materials);
  socket.name = hand + "Wrist";
  pair.add(socket);
  for (const part of socket.children)
    part.name =
      hand + " " + (part as T.Mesh<T.BufferGeometry, T.Material>).material.name;
}
// Sample the same cubic easing as the runtime at 60 Hz. glTF rotations
// interpolate on the unit sphere, so keep quaternion signs continuous.
const clips = BOSSES[1].attacks.map((attack) => {
  const tracks: T.KeyframeTrack[] = [];
  for (const hand of hands) {
    const times: number[] = [],
      pos: number[] = [],
      rot: number[] = [];
    const q = new T.Quaternion(),
      last = new T.Quaternion(),
      dir = new T.Vector3();
    let offset = 0;
    for (const [phase, duration] of [
      ["windup", attack.windup],
      ["active", attack.active],
      ["recover", attack.recovery],
    ] as const) {
      const keys = heronStroke(attack.shape, phase, hand)!;
      for (let k = 1; k < keys.length; k++) {
        const a = keys[k - 1],
          b = keys[k],
          n = Math.ceil((b[0] - a[0]) * duration * 60);
        for (let j = times.length ? 1 : 0; j <= n; j++) {
          const u = j / n,
            f = u * u * (3 - 2 * u);
          const v = (i: number) => T.MathUtils.lerp(a[i], b[i], f);
          times.push(offset + T.MathUtils.lerp(a[0], b[0], u) * duration);
          pos.push(v(1), v(2), v(3));
          const yaw = v(4),
            pitch = v(5);
          dir.set(
            Math.sin(yaw) * Math.cos(pitch),
            Math.sin(pitch),
            Math.cos(yaw) * Math.cos(pitch),
          );
          q.setFromUnitVectors(up, dir);
          if (last.dot(q) < 0) q.set(-q.x, -q.y, -q.z, -q.w);
          rot.push(...q.toArray());
          last.copy(q);
        }
      }
      offset += duration;
    }
    const node = pair.getObjectByName(hand + "Wrist")!;
    node.position.fromArray(pos);
    node.quaternion.fromArray(rot);
    tracks.push(
      new T.VectorKeyframeTrack(node.name + ".position", times, pos),
      new T.QuaternionKeyframeTrack(node.name + ".quaternion", times, rot),
    );
  }
  return new T.AnimationClip(attack.name, -1, tracks);
});
await bake(pair, "HeronSabres", clips);
