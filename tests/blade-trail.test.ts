import assert from "node:assert/strict";
import test from "node:test";
import * as T from "three";
import { BladeTrail } from "../src/pilgrim";
import { jianPoint } from "../src/pilgrim-jian";

test("the trail samples only the point, fades by age and drops discontinuous poses", () => {
  const sword = new T.Group();
  for (const fps of [30, 60, 120]) {
    const trail = new BladeTrail();
    const steps = Math.ceil(fps * 0.14);
    for (let i = 0; i <= steps; i++) {
      sword.position.x = (15 * i) / fps;
      trail.sample(sword, "light", 0.22 + (0.18 * i) / steps, i / fps);
    }
    assert.equal(trail.visible, true);
    const rows = trail.geometry.drawRange.count / 6 + 1;
    const position = trail.geometry.getAttribute("position");
    const color = trail.geometry.getAttribute("color");
    for (let i = 0; i < rows; i++) {
      assert.ok(
        Math.abs(position.getY(i * 2 + 1) - (jianPoint - 0.015)) < 1e-6,
      );
      assert.ok(Math.abs(position.getY(i * 2) - (jianPoint - 0.12)) < 1e-6);
      assert.equal(color.getW(i * 2), 0);
      if (i) assert.ok(color.getW(i * 2 + 1) < color.getW(i * 2 - 1));
    }
    assert.ok(position.getX(0) - position.getX(2 * rows - 2) <= 15 * 0.05);
    const last = steps / fps;
    trail.sample(sword, "light", 0.41, last + 0.2);
    assert.equal(trail.visible, false);
    sword.position.x += 0.25;
    trail.sample(sword, "light", 0.43, last + 0.22);
    assert.equal(trail.visible, true);
    trail.sample(sword, "heavy", 0.46, last + 0.23);
    assert.equal(trail.visible, false);
    trail.sample(sword, "idle", 0, last + 0.24);
    assert.equal(trail.geometry.drawRange.count, 0);
  }
});
