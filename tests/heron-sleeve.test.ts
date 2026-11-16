import assert from "node:assert/strict";
import test from "node:test";
import * as T from "three";
import { heronSleeve } from "../src/heron-sleeve";

test("the shoulder stays on the upper arm while the sleeve cuff follows the blade wrist", () => {
  const root = new T.Group(), upper = new T.Bone(), forearm = new T.Bone(), wrist = new T.Bone();
  root.add(upper);
  upper.add(forearm);
  forearm.add(wrist);
  upper.position.set(0.3, 2.4, 0);
  forearm.position.x = 0.47;
  wrist.position.x = 0.4;
  root.updateMatrixWorld(true);
  const material = new T.MeshStandardMaterial();
  const sleeve = heronSleeve(root, upper, forearm, wrist, 1, material, material, material);
  const positions = sleeve.geometry.getAttribute("position");
  const cuffIndex = positions.count - 1;
  const shoulder = sleeve.getVertexPosition(0, new T.Vector3());
  const cuff = sleeve.getVertexPosition(cuffIndex, new T.Vector3());
  const bindOffset = wrist.worldToLocal(cuff.clone());
  forearm.rotation.z = Math.PI * 0.55;
  root.updateMatrixWorld(true);
  assert.ok(sleeve.getVertexPosition(0, new T.Vector3()).distanceTo(shoulder) < 1e-5);
  assert.ok(sleeve.getVertexPosition(cuffIndex, new T.Vector3()).distanceTo(wrist.localToWorld(bindOffset)) < 1e-5);
  assert.ok(sleeve.getVertexPosition(cuffIndex, new T.Vector3()).distanceTo(cuff) > 0.3);
  sleeve.geometry.dispose();
  material.dispose();
});
