import * as T from "three";

// A flush apron laid in staggered radial courses. The sloping edges terminate
// above the cobble bed so combat and floor-level attack indicators share a plane.
export function courtPaving(random: () => number) {
  const positions: number[] = [], uvs: number[] = [], colors: number[] = [], indices: number[] = [];
  const edges = [6.36, 6.71, 7.68, 8.74, 9.68, 10.76, 11.85, 12.70];
  const tau = Math.PI * 2;
  for (let course = 0; course < edges.length - 1; course++) {
    const inner = edges[course], outer = edges[course + 1];
    const count = Math.round((inner + outer) * Math.PI / (course === 0 ? 1.03 : 1.77));
    const knots = Array.from({length: count}, (_, i) =>
      (i + 0.38 * course + (random() - 0.5) * 0.27) * tau / count);
    knots.push(knots[0] + tau);
    for (let slab = 0; slab < count; slab++) {
      const start = knots[slab] + .011 / inner, end = knots[slab + 1] - .011 / inner;
      const height = -.018 + .014 * random(), tone = .75 + .25 * random();
      const angle = random() * tau, du = random(), dv = random();
      const first = positions.length / 3;
      // Four cross-sections form the bevel, the flat face and the outer bevel.
      for (const [rad, h, inset, shade] of [
        [inner + .009, -.053, 0, .67], [inner + .033, height, .026, 1],
        [outer - .033, height, .026, 1], [outer - .009, -.053, 0, .67],
      ]) {
        for (let j = 0; j <= 6; j++) {
          const a = start + inset/rad + (end - start - 2*inset/rad)*j/6;
          const x = rad*Math.cos(a), z = rad*Math.sin(a);
          positions.push(x, h, z);
          uvs.push(du+(x*Math.cos(angle)-z*Math.sin(angle))*.43, dv+(x*Math.sin(angle)+z*Math.cos(angle))*.43);
          colors.push(tone*shade, tone*shade, tone*shade);
        }
      }
      for (let row = 0; row < 3; row++) {
        for (let j = 0; j < 6; j++) {
          const a = first + row * 7 + j;
          indices.push(a, a + 1, a + 7, a + 1, a + 8, a + 7);
        }
      }
      // Close the two short broken edges against the mortar in each joint.
      indices.push(first, first+7, first+14, first, first+14, first+21);
      indices.push(first+6, first+20, first+13, first+6, first+27, first+20);
    }
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
  geometry.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

/** A shallow gutter follows the last stone course. Cast grates bridge its four
 * outlets; the openings reveal the dark channel bed between the bronze bars. */
export function runoffChannel(metal: T.Material, kerb: T.Material) {
  const gutter = new T.Group();
  const bed = new T.MeshBasicMaterial({ color: 0x171d1d });
  const annulus = (
    inner: number,
    outer: number,
    height: number,
    material: T.Material,
  ) => {
    const g = new T.RingGeometry(inner, outer, 192);
    g.rotateX(-Math.PI / 2);
    const m = new T.Mesh(g, material);
    m.position.y = height;
    m.receiveShadow = true;
    gutter.add(m);
  };
  annulus(12.59, 13.14, -0.002, bed);
  annulus(12.56, 12.62, 0.026, kerb);
  annulus(12.65, 12.67, 0.004, metal);
  const bars: T.Matrix4[] = [];
  const stones: T.Matrix4[] = [];
  const transform = new T.Object3D();
  function piece(
    batch: T.Matrix4[],
    angle: number,
    r: number,
    y: number,
    w: number,
    h: number,
    d: number,
    turn = 0,
  ) {
    transform.position.set(Math.sin(angle) * r, y, Math.cos(angle) * r);
    transform.rotation.set(0, angle + turn, 0);
    transform.scale.set(w, h, d);
    transform.updateMatrix();
    batch.push(transform.matrix.clone());
  }
  // Short gaps in the curb line up with the four cast intake grilles.
  for (let i = 0; i < 96; i++) {
    const a = (i * Math.PI) / 48;
    if (i % 24 === 0) continue;
    piece(stones, a, 13.03, 0.064, 0.825, 0.15, 0.32);
    piece(stones, a, 13.06, 0.155, 0.83, 0.045, 0.37);
  }
  for (let side = 0; side < 4; side++) {
    const a = (side * Math.PI) / 2;
    for (const r of [12.63, 13.15])
      piece(bars, a, r, 0.065, 0.94, 0.056, 0.056);
    for (let i = -5; i <= 5; i++)
      piece(bars, a + i * 0.0066, 12.89, 0.063, 0.034, 0.048, 0.54);
    for (const sign of [-1, 1])
      piece(
        bars,
        a + sign * 0.016,
        12.89,
        0.093,
        0.026,
        0.022,
        0.53,
        sign * 0.63,
      );
  }
  function instances(matrices: T.Matrix4[], material: T.Material) {
    const mesh = new T.InstancedMesh(
      new T.BoxGeometry(),
      material,
      matrices.length,
    );
    matrices.forEach((matrix, i) => mesh.setMatrixAt(i, matrix));
    mesh.castShadow = mesh.receiveShadow = true;
    gutter.add(mesh);
  }
  instances(stones, kerb);
  instances(bars, metal);
  return gutter;
}
