import test from "node:test";
import assert from "node:assert/strict";
import * as T from "three";
import { lotusGarden } from "../src/lotus-garden";
import { waterGallery } from "../src/landmarks";

test("the west gallery roof has finite positions through the overlapping last tile course", () => {
  const mat = new T.MeshStandardMaterial();
  const gallery = waterGallery(
    { rock: mat, wall: mat, dark: mat },
    mat,
    mat,
    mat,
  );
  gallery.traverse((part) => {
    if (!(part instanceof T.Mesh)) return;
    assert.ok(part.geometry.attributes.position.array.every(Number.isFinite));
    part.geometry.dispose();
  });
  mat.dispose();
});

test("both pool surfaces stay beyond the last course of arena paving", () => {
  const mat = new T.MeshStandardMaterial(),
    map = new T.Texture();
  const { pools, banks } = lotusGarden(mat, mat, map, () => 0.4);
  assert.equal(pools.children.length, 2);
  for (const surface of pools.children) {
    const p = (surface as T.Mesh).geometry.attributes.position;
    for (let i = 0; i < p.count; i++)
      assert.ok(Math.hypot(p.getX(i), p.getZ(i)) > 13.14);
  }
  for (const group of [pools, banks])
    group.traverse((part) => {
      if (!(part instanceof T.Mesh)) return;
      assert.ok(part.geometry.attributes.position.array.every(Number.isFinite));
      part.geometry.dispose();
    });
  mat.dispose();
  map.dispose();
});
