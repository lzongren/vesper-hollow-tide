import assert from "node:assert/strict";
import test from "node:test";
import { PointLight } from "three";
import { Combat } from "../src/combat";
import { CinderLights } from "../src/cinder-fire";

test("shrine light sources follow all eight awakened vents from ignition to extinction", () => {
  const game = new Combat(2);
  game.boss.phase = 2;
  game.boss.attack = 2;
  game.emitAttack();
  const rig = new CinderLights();
  const lamps = rig.children as PointLight[];
  assert.equal(game.hazards.length, lamps.length);
  rig.update(game.hazards);
  assert.ok(lamps.every(light => light.intensity === 0));
  for (const h of game.hazards) h.age = h.delay + .35;
  rig.update(game.hazards);
  lamps.forEach((lamp, i) => {
    assert.equal(lamp.position.x, game.hazards[i].x);
    assert.equal(lamp.position.z, game.hazards[i].z);
    assert.ok(lamp.intensity > 30 && lamp.position.y > 1);
  });
  for (const h of game.hazards) h.age = h.life;
  rig.update(game.hazards);
  assert.ok(lamps.every(light => light.intensity === 0));
  rig.update([]);
  assert.equal(rig.children.length, 8);
});
