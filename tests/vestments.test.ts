import assert from "node:assert/strict";
import test from "node:test";
import * as T from "three";
import { BOSSES } from "../src/combat";
import { mantleGeometry } from "../src/pilgrim";
import { bellStroke, MantleMotion } from "../src/vestments";
import { warningFiligree } from "../src/rites";

test("the bell pose matches on both sides of the damage and recovery transitions", () => {
  for (const attack of BOSSES[0].attacks) {
    const lift = bellStroke(attack.shape, "windup")!;
    const strike = bellStroke(attack.shape, "active")!;
    const settle = bellStroke(attack.shape, "recover")!;
    assert.deepEqual(lift.at(-1)!.slice(1), strike[0].slice(1));
    assert.deepEqual(strike.at(-1)!.slice(1), settle[0].slice(1));
    assert.deepEqual(settle.at(-1)!.slice(1), lift[0].slice(1));
  }
});

test("mantle pins the shoulders and drags the hem away from a lateral step", () => {
  const mesh = new T.Mesh(mantleGeometry()),
    motion = new MantleMotion(mesh);
  const p = mesh.geometry.attributes.position,
    base = new Float32Array(p.array);
  const bottom = p.count - 1;
  for (let i = 0; i <= 32; i++) motion.step(i * 0.045, 0, 0, 1 / 60, i / 60, 0);
  assert.deepEqual(
    Array.from(p.array.slice(0, 3)),
    Array.from(base.slice(0, 3)),
  );
  assert.ok(p.getX(bottom) < base[bottom * 3] - 0.04);
  motion.step(30, 0, 0, 1 / 60, 1, 0);
  assert.ok(Math.abs(p.getX(bottom) - base[bottom * 3]) < 0.001);
});

test("sweep filigree lies on the floor and its outer endpoints match the combat sector", () => {
  const attack = BOSSES[0].attacks[0];
  const warning = warningFiligree(attack);
  const first = warning.children[0] as T.Mesh;
  const p = first.geometry.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i),
      z = p.getZ(i);
    assert.ok(Math.abs(p.getY(i)) < 1e-5);
    assert.ok(Math.abs(Math.atan2(x, z)) <= attack.arc / 2 + 0.0001);
    assert.ok(Math.hypot(x, z) <= attack.range + 0.0001);
  }
  for (const sign of [-1, 1])
    assert.ok(
      Array.from({ length: p.count }, (_, i) => i).some(
        (i) =>
          Math.abs(Math.hypot(p.getX(i), p.getZ(i)) - attack.range) < 0.0001 &&
          Math.abs(Math.atan2(p.getX(i), p.getZ(i)) - (sign * attack.arc) / 2) <
            0.0001,
      ),
    );
});
