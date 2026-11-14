import assert from "node:assert/strict";
import test from "node:test";
import * as T from "three";
import { flagstoneSeal } from "../src/flagstone-seal";

test("the jointed seal preserves mural registration and the combat ground plane", () => {
  const g = flagstoneSeal(() => 0.48);
  const p = g.getAttribute("position"), uv = g.getAttribute("uv");
  const index = g.getIndex()!;
  const a = new T.Vector3(), b = new T.Vector3(), c = new T.Vector3();
  let projectedArea = 0;
  for (let i = 0; i < index.count; i += 3) {
    a.fromBufferAttribute(p, index.getX(i));
    b.fromBufferAttribute(p, index.getX(i + 1));
    c.fromBufferAttribute(p, index.getX(i + 2));
    const up = b.sub(a).cross(c.sub(a)).y;
    assert.ok(up > 0, "stone faces must survive front-face culling");
    projectedArea += up / 2;
  }
  const discArea = Math.PI * 6.35 ** 2;
  assert.ok(projectedArea > discArea * 0.96 && projectedArea < discArea);
  for (let i = 0; i < p.count; i++) {
    assert.ok(p.getY(i) > -0.06 && p.getY(i) < 0.01);
    assert.ok(Math.abs(uv.getX(i) - 0.5 - p.getX(i) / 12.7) < 1e-6);
    assert.ok(Math.abs(uv.getY(i) - 0.5 + p.getZ(i) / 12.7) < 1e-6);
  }
});
