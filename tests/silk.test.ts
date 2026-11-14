import { RainCape } from "../src/rain-cape";
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

test("every sewn palm strip follows a translation of its cloth surface", () => {
  const panel = new T.PlaneGeometry(0.8, 0.45, 32, 32);
  const cape = new RainCape(panel);
  const source = panel.attributes.position as T.BufferAttribute;
  const dest = cape.geometry.attributes.position;
  const rest = new Float32Array(dest.array);
  const shift = new T.Vector3(0.13, -0.05, 0.21);
  for (let i = 0; i < source.count; i++) {
    source.setXYZ(
      i,
      source.getX(i) + shift.x,
      source.getY(i) + shift.y,
      source.getZ(i) + shift.z,
    );
  }
  cape.fit(source);
  for (let i = 0; i < dest.count; i++) {
    assert.ok(Math.abs(dest.getX(i) - rest[3 * i] - shift.x) < 1e-6);
    assert.ok(Math.abs(dest.getY(i) - rest[3 * i + 1] - shift.y) < 1e-6);
    assert.ok(Math.abs(dest.getZ(i) - rest[3 * i + 2] - shift.z) < 1e-6);
  }
  cape.geometry.dispose();
  cape.material.dispose();
  panel.dispose();
});
