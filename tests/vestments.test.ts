import assert from "node:assert/strict";
import test from "node:test";
import * as T from "three";
import { BOSSES, Combat, DASH_SPEED, DASH_REACH, inSector, SLAM_MARGIN } from "../src/combat";
import { mantleGeometry } from "../src/pilgrim";
import { bellStroke, MantleMotion } from "../src/vestments";
import { GroundRite } from "../src/rites";

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

test("paving wave follows boss facing, hit reach and remaining charge travel", () => {
  const game = new Combat(0), rite = new GroundRite(), boss = game.boss;
  game.mode = "combat";
  for (const attack of [0, 1, 2]) {
    game.beginAttack(attack);
    boss.facing = 0.7;
    rite.update(game);
    const [radius, width, shape] = rite.extent.value.toArray();
    assert.deepEqual(rite.pose.value.toArray(), [boss.x, boss.z, Math.sin(.7), Math.cos(.7)]);
    if (shape === 1) {
      for (const direction of [-1, 1]) {
        const a = boss.facing + direction * (width - 1e-5);
        const point = (r: number) => ({x: boss.x + r * Math.sin(a), z: boss.z + r * Math.cos(a)});
        assert.ok(inSector(boss, point(radius - .001), boss.facing, game.attack.range, game.attack.arc));
        assert.ok(!inSector(boss, point(radius + .001), boss.facing, game.attack.range, game.attack.arc));
      }
    } else if (shape === 0) {
      assert.equal(radius, game.attack.range + SLAM_MARGIN);
    } else {
      assert.equal(width, DASH_REACH);
      boss.state = "active";
      boss.timer = .2;
      rite.update(game);
      assert.equal(rite.extent.value.x, (game.attack.active - .2) * DASH_SPEED);
    }
    boss.state = "recover";
    rite.update(game);
    assert.equal(rite.charge.value, 0);
  }
});
