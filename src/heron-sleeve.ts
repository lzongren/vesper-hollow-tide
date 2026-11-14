import * as T from "three";

/** A continuous silk sleeve bound to the same arm that drives the sabre.
 * The outside seam opens into a hanging pocket and gathers at the wrist. */
export function heronSleeve(
  root: T.Group,
  upper: T.Bone,
  forearm: T.Bone,
  wrist: T.Bone,
  side: number,
  silk: T.Material,
  brocade: T.Material,
  trim: T.Material,
) {
  const jointPoint = (joint: T.Bone) => root.worldToLocal(joint.getWorldPosition(new T.Vector3()));
  const shoulder = jointPoint(upper), elbow = jointPoint(forearm), hand = jointPoint(wrist);
  const first = elbow.clone().sub(shoulder), second = hand.clone().sub(elbow);
  const upperAxis = first.clone().normalize(), lowerAxis = second.clone().normalize();
  const bend = first.length() / (first.length() + second.length());
  const rows = 72, columns = 56;
  const position: number[] = [], uv: number[] = [], weights: number[] = [], joints: number[] = [];
  const faces: number[][] = [[], [], []];
  const along = new T.Vector3(), down = new T.Vector3(), front = new T.Vector3();
  const center = new T.Vector3(), offset = new T.Vector3();
  const gauss = (value: number, at: number, width: number) => Math.exp(-(((value - at) / width) ** 2));
  const ease = T.MathUtils.smoothstep;
  for (let row = 0; row <= rows; row++) {
    const t = row / rows;
    if (t <= bend) center.copy(shoulder).addScaledVector(first, t / bend);
    else center.copy(elbow).addScaledVector(second, (t - bend) / (1 - bend));
    // Extend the cap into the shoulder and stop just inside the palm.
    center.addScaledVector(first, -0.075 * (1 - ease(t, 0, 0.13)));
    along.copy(upperAxis).lerp(lowerAxis, ease(t, bend - 0.09, bend + 0.09)).normalize();
    down.set(0, -1, 0).addScaledVector(along, along.y).normalize();
    front.crossVectors(along, down).normalize();
    const turned = ease(t, bend - 0.12, bend + 0.12);
    const expansion = Math.sin(Math.PI * Math.pow(t, 0.77));
    for (let col = 0; col <= columns; col++) {
      const theta = 2 * Math.PI * col / columns, c = Math.cos(theta), s = Math.sin(theta);
      const below = Math.max(0, c);
      const drape = expansion * (0.05 + 0.15 * below ** 2);
      const winding = theta + side * (0.44 * t + 0.21 * Math.sin(4.1 * t));
      const flute = (0.009 + 0.016 * below) * expansion *
        (Math.cos(7 * winding) + 0.42 * Math.cos(11 * winding - 2 * t));
      const crease = 0.015 * Math.cos(48 * t + 2.7 * Math.sin(theta)) *
        (gauss(t, bend, 0.18) + 0.77 * gauss(t, 0.8, 0.14));
      const base = 0.058 + 0.063 * (1 - t) + 0.038 * gauss(t, 0.17, 0.16);
      const radius = base + drape + flute + crease;
      offset.copy(center).addScaledVector(down, c * radius)
        .addScaledVector(front, s * (base + 0.42 * drape + flute + crease));
      position.push(offset.x, offset.y, offset.z);
      uv.push(col / columns, 1 - t);
      joints.push(0, 1, 0, 0);
      weights.push(1 - turned, turned, 0, 0);
      if (row < rows && col < columns) {
        const mid = (row + 0.5) / rows;
        const shoulderEdge = 0.24 + 0.045 * Math.cos(theta * 4);
        const piping = Math.abs(mid - shoulderEdge) < 0.008 || Math.abs(mid - 0.87) < 0.008 || mid > 0.977;
        const material = piping ? 2 : mid < shoulderEdge || mid > 0.87 ? 1 : 0;
        const a = row * (columns + 1) + col, b = a + columns + 1;
        faces[material].push(a, a + 1, b, a + 1, b + 1, b);
      }
    }
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.Float32BufferAttribute(position, 3));
  geometry.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
  geometry.setAttribute("skinIndex", new T.Uint16BufferAttribute(joints, 4));
  geometry.setAttribute("skinWeight", new T.Float32BufferAttribute(weights, 4));
  geometry.setIndex(faces.flat());
  let start = 0;
  faces.forEach((indices, index) => {
    geometry.addGroup(start, indices.length, index);
    start += indices.length;
  });
  geometry.computeVertexNormals();
  // The texture seam duplicates vertices. Average both normals at the join.
  const normals = geometry.getAttribute("normal");
  const v = new T.Vector3(), w = new T.Vector3();
  for (let row = 0; row <= rows; row++) {
    const a = row * (columns + 1), b = a + columns;
    v.fromBufferAttribute(normals, a).add(w.fromBufferAttribute(normals, b)).normalize();
    normals.setXYZ(a, v.x, v.y, v.z);
    normals.setXYZ(b, v.x, v.y, v.z);
  }
  const sleeve = new T.SkinnedMesh(geometry, [silk, brocade, trim]);
  sleeve.name = side > 0 ? "Left silk sleeve" : "Right silk sleeve";
  root.add(sleeve);
  root.updateWorldMatrix(true, true);
  sleeve.bind(new T.Skeleton([upper, forearm]), sleeve.matrixWorld);
  sleeve.frustumCulled = false;
  sleeve.castShadow = sleeve.receiveShadow = true;
  geometry.addEventListener("dispose", () => sleeve.skeleton.dispose());
  return sleeve;
}
