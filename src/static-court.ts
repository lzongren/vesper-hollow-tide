import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** Keep nearby opaque architectural details together for the beauty, shadow
 * and reflection passes. Movable and asset-library meshes retain their owners. */
export function batchCourt(root: T.Group, animated: Set<T.Mesh>) {
  root.updateWorldMatrix(true, true);
  const inverse = root.matrixWorld.clone().invert();
  const groups = new Map<string, T.Mesh<T.BufferGeometry, T.Material>[]>();
  root.traverse((o) => {
    if (
      !(o instanceof T.Mesh) ||
      o instanceof T.InstancedMesh ||
      o instanceof T.SkinnedMesh ||
      animated.has(o) ||
      o.userData.sharedGeometry ||
      o.children.length ||
      Array.isArray(o.material) ||
      o.material.transparent ||
      o.geometry.morphAttributes.position
    )
      return;
    const p = new T.Vector3().setFromMatrixPosition(o.matrixWorld);
    const key = [
      o.material.uuid,
      o.castShadow,
      o.receiveShadow,
      Object.keys(o.geometry.attributes).sort().join(","),
      Math.floor(p.x / 12),
      Math.floor(p.z / 12),
    ].join("/");
    let group = groups.get(key);
    if (!group) groups.set(key, (group = []));
    group.push(o);
  });
  const removed = new Set<T.BufferGeometry>();
  for (const batch of groups.values()) {
    if (batch.length < 3) continue;
    const parts = batch.map((mesh) => {
      const geometry = mesh.geometry.index
        ? mesh.geometry.toNonIndexed()
        : mesh.geometry.clone();
      return geometry.applyMatrix4(
        new T.Matrix4().multiplyMatrices(inverse, mesh.matrixWorld),
      );
    });
    const combined = mergeGeometries(parts);
    parts.forEach((g) => g.dispose());
    if (!combined) continue;
    const source = batch[0],
      result = new T.Mesh(combined, source.material);
    result.castShadow = source.castShadow;
    result.receiveShadow = source.receiveShadow;
    result.name = "Batched court details";
    batch.forEach((mesh) => {
      mesh.removeFromParent();
      removed.add(mesh.geometry);
    });
    root.add(result);
  }
  root.traverse((o) => {
    if (o instanceof T.Mesh) removed.delete(o.geometry);
  });
  removed.forEach((g) => g.dispose());
}
