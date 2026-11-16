import assert from "node:assert/strict";
import test from "node:test";
import * as T from "three";
import { BladeImpact } from "../src/blade-impact";

test("contact uses the facing surface and reuses a bounded buffer across hits and retries", () => {
  const effect = new BladeImpact(), blade = new T.Group();
  const eye = new T.Vector3(-1, 2, 4);
  blade.position.set(0, 1.1, 0.60);
  blade.rotation.x = -Math.PI / 2;
  effect.track(blade);
  blade.position.x += 0.08;
  effect.track(blade);
  const strike = (quiet: boolean) => effect.strike(blade, new T.Vector3(), 3.9, 0, 24, false, quiet);
  strike(true);
  effect.advance(0, eye);
  assert.equal(effect.geometry.drawRange.count, 7 * 6);
  const positions = effect.geometry.getAttribute("position");
  // The second vertex lies at the contact point plus one narrow fragment width.
  assert.ok(positions.getZ(1) > 0.78);
  for (let i = 0; i < 16; i++) strike(false);
  effect.advance(1 / 60, eye);
  assert.equal(effect.geometry.drawRange.count, 80 * 6);
  assert.equal(effect.geometry.getAttribute("position"), positions);
  effect.advance(1, eye);
  assert.equal(effect.visible, false);
  strike(false);
  effect.clearBursts();
  effect.advance(0, eye);
  assert.equal(effect.geometry.drawRange.count, 0);
});
