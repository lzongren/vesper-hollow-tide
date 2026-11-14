import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import * as T from "three";
import { Footwork } from "../src/footwork";

// Rebuild the authored GLB node hierarchy, including the scaled armature parent.
function rig(name: string) {
  const file = readFileSync(
    new URL("../public/models/" + name + ".glb", import.meta.url),
  );
  const gltf = JSON.parse(
    file.subarray(20, 20 + file.readUInt32LE(12)).toString(),
  );
  type Node = {
    name: string;
    matrix?: number[];
    translation?: number[];
    rotation?: number[];
    scale?: number[];
    children?: number[];
  };
  const defs: Node[] = gltf.nodes;
  const nodes = defs.map((def) => {
    const n = new T.Bone();
    n.name = def.name;
    if (def.matrix)
      new T.Matrix4()
        .fromArray(def.matrix)
        .decompose(n.position, n.quaternion, n.scale);
    if (def.translation) n.position.fromArray(def.translation);
    if (def.rotation) n.quaternion.fromArray(def.rotation);
    if (def.scale) n.scale.fromArray(def.scale);
    return n;
  });
  defs.forEach((def, i) =>
    def.children?.forEach((j) => nodes[i].add(nodes[j])),
  );
  const root = new T.Group(),
    model = new T.Group();
  root.add(model);
  for (const i of gltf.scenes[gltf.scene || 0].nodes) model.add(nodes[i]);
  const bones = new Map(nodes.map((n) => [n.name, n]));
  const pos = (key: string) =>
    bones.get(key)!.getWorldPosition(new T.Vector3());
  model.scale.setScalar(1.65 / (pos("Head").y - pos("LeftFoot").y));
  model.position.y = 0.12 - pos("LeftFoot").y;
  const rest = nodes.map((n) => n.quaternion.clone());
  const gait = new Footwork(root, bones, 1.9);
  function frame(x: number, yaw: number, dt: number) {
    root.position.set(x, 0, 0);
    root.rotation.y = yaw;
    nodes.forEach((n, i) => n.quaternion.copy(rest[i]));
    const landing = gait.pose(dt);
    return {
      left: pos("LeftFoot"),
      right: pos("RightFoot"),
      landing: landing?.clone(),
    };
  }
  return { frame, gait };
}

for (const name of ["pilgrim", "wraith", "sorcerer"])
  test(
    name + " plant, sidestep, stop and respawn on the authored leg chains",
    () => {
      const { frame, gait } = rig(name);
      let prev = frame(0, 0, 1 / 60),
        dt = 1 / 60,
        x = 0,
        contacts = 0,
        plantedFrames = 0;
      for (let i = 0; i < 150; i++) {
        dt = i % 3 === 0 ? 1 / 45 : 1 / 60;
        if (i < 90) x += 1.9 * dt;
        const current = frame(x, Math.min(i * 0.004, 0.36), dt);
        if (current.landing) {
          contacts++;
          assert.ok(
            Math.min(
              current.left.distanceTo(current.landing),
              current.right.distanceTo(current.landing),
            ) < 0.018,
          );
        }
        if (
          Math.min(
            current.left.distanceTo(prev.left),
            current.right.distanceTo(prev.right),
          ) < 0.004
        )
          plantedFrames++;
        if (i > 130) {
          assert.ok(current.left.distanceTo(prev.left) < 0.00001);
          assert.ok(current.right.distanceTo(prev.right) < 0.00001);
        }
        prev = current;
      }
      assert.ok(contacts >= 6 && contacts <= 17);
      assert.ok(plantedFrames > 138, `planted ${plantedFrames}/150 frames`);
      gait.reset();
      const respawn = frame(-15, 1, dt);
      assert.equal(respawn.landing, undefined);
      assert.ok(
        Math.abs(respawn.left.x + 15) < 1 && Math.abs(respawn.right.x + 15) < 1,
      );
    },
  );
