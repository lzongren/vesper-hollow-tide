import { strict as assert } from "node:assert";
import test from "node:test";
import * as T from "three";
import { batchCourt } from "../src/static-court";

test("court batching preserves transformed bounds and animated and library meshes", () => {
  const root = new T.Group(),
    group = new T.Group();
  root.add(group);
  root.position.set(4, 0, 1);
  group.position.set(1, 0, 2);
  group.rotation.y = 0.35;
  const material = new T.MeshStandardMaterial(),
    geo = new T.BoxGeometry();
  const fixtures = Array.from({ length: 6 }, (_, i) => {
    const mesh = new T.Mesh(geo, material);
    mesh.position.set(i * 0.32, 0.5, i * 0.14);
    group.add(mesh);
    return mesh;
  });
  fixtures[4].userData.sharedGeometry = true;
  let disposed = false;
  geo.addEventListener("dispose", () => {
    disposed = true;
  });
  const before = new T.Box3().setFromObject(root, true);
  batchCourt(root, new Set([fixtures[5]]));
  const after = new T.Box3().setFromObject(root, true);
  assert.ok(
    before.min.distanceTo(after.min) < 1e-6 &&
      before.max.distanceTo(after.max) < 1e-6,
  );
  assert.equal(fixtures[4].parent, group);
  assert.equal(fixtures[5].parent, group);
  assert.equal(root.getObjectByName("Batched court details")?.parent, root);
  assert.equal(disposed, false);
});
