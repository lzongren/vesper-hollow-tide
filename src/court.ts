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
