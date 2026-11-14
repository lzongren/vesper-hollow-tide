import assert from "node:assert/strict";
import test from "node:test";
import * as T from "three";
import { SilkPanel } from "../src/silk";

test("a raised elbow lifts its own shoulder while the skirt lags through a turn and resets on teleport", () => {
  const root = new T.Group(),
    spine = new T.Bone(),
    r = new T.Bone(),
    l = new T.Bone(),
    h = 3.9;
  root.add(spine, r, l);
  r.position.set(-0.17 * h, 0.6 * h, 0);
  l.position.set(0.17 * h, 0.6 * h, 0);
  const panel = new SilkPanel(
    root,
    spine,
    { side: 0, back: true, shoulder: true },
    h,
    new T.MeshStandardMaterial(),
    [],
    [r, l],
  );
  const positions = panel.mesh.geometry.attributes.position;
  const point = (i: number) =>
    new T.Vector3().fromBufferAttribute(positions, i);
  for (let i = 0; i < 60; i++) panel.update(1 / 60, i / 60);
  const p0 = point(0),
    p1 = point(32),
    bottom = point(32 * 33 + 16);
  r.position.y = 0.91 * h;
  panel.update(1 / 60, 1);
  assert.ok(point(0).y > p0.y + 0.075 * h);
  assert.ok(point(32).distanceTo(p1) < 0.00001);
  root.rotation.y = 0.55;
  root.position.x = 0.12;
  panel.update(1 / 60, 1.02);
  assert.ok(point(32 * 33 + 16).distanceTo(bottom) > 0.1);
  for (const dt of [1 / 30, 1 / 144, 0.045, 1 / 60]) {
    root.position.set(23, 0, -12);
    panel.update(dt, 2);
    for (let i = 0; i < positions.count; i++) {
      const p = point(i);
      assert.ok(p.length() < h * 1.08 && p.y > 0);
    }
  }
});
