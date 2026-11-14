import * as T from "three";

const radius = 6.35;
const tau = Math.PI * 2;
const courses = [0.62, 1.82, 3.24, 4.52, 5.65, radius];
const counts = [1, 7, 11, 16, 21, 26];

/** Fitted stones retaining the original mural in court coordinates. Each bed
 * has an individual fall, a chipped arris and a worn, slightly convex top. */
export function flagstoneSeal(random: () => number) {
  const points: number[] = [], colors: number[] = [], uvs: number[] = [], indices: number[] = [];
  function vertex(x: number, z: number, y: number, value: number) {
    const index = points.length / 3;
    points.push(x, y, z);
    uvs.push(0.5 + x / (2 * radius), 0.5 - z / (2 * radius));
    colors.push(value, value, value);
    return index;
  }
  function strip(a: number, b: number, c: number, d: number) {
    indices.push(a, b, c, b, d, c);
  }
  for (let course = 0; course < courses.length; course++) {
    const inner = courses[course - 1] ?? 0, outer = courses[course];
    const count = counts[course], offset = course * 0.41;
    const knots = Array.from({ length: count }, (_, i) =>
      (i + offset + (random() - 0.5) * 0.22) * tau / count);
    knots.push(knots[0] + tau);
    for (let k = 0; k < count; k++) {
      const start = knots[k], span = knots[k + 1] - start;
      const height = -0.018 + random() * 0.014;
      const tone = 0.78 + 0.22 * random(), fall = (random() - 0.5) * 0.013;
      if (course === 0) {
        const center = vertex(0, 0, height + 0.006, tone);
        let previous: number[] = [];
        for (let j = 0; j <= 96; j++) {
          const a = tau * j / 96, x = Math.cos(a), z = Math.sin(a);
          const row = [
            vertex((outer - 0.034) * x, (outer - 0.034) * z, height, tone),
            vertex((outer - 0.009) * x, (outer - 0.009) * z, -0.045, tone * 0.65),
          ];
          if (j) {
            indices.push(center, row[0], previous[0]);
            strip(previous[0], row[0], previous[1], row[1]);
          }
          previous = row;
        }
        continue;
      }
      const slices = Math.ceil(span * outer / 0.12);
      // Include both short bevels. The first/last stations descend to the bed.
      const bevel = 0.027 / (span * (outer + inner) * 0.5);
      const stations = [0, ...Array.from({ length: slices + 1 }, (_, j) =>
        bevel + (1 - 2 * bevel) * j / slices), 1];
      let previous: number[] = [];
      for (const s of stations) {
        const angle = start + span * s + (0.5 - s) * 0.018 / ((inner + outer) * 0.5);
        const chipped = 0.009 + 0.019 * random() ** 3;
        const lowEnd = s === 0 || s === 1;
        const row = [inner + 0.009, inner + 0.024 + chipped, (inner + outer) * 0.5,
          outer - 0.024 - chipped, outer - 0.009].map((r, i) => {
          const low = i === 0 || i === 4 || lowEnd;
          const top = height + fall * (s - 0.5) + (i === 2 ? 0.006 : 0);
          return vertex(r * Math.cos(angle), r * Math.sin(angle),
            low ? -0.036 : top, tone * (low ? 0.76 : 1));
        });
        if (previous.length)
          for (let i = 0; i < row.length - 1; i++)
            strip(previous[i], row[i], previous[i + 1], row[i + 1]);
        previous = row;
      }
    }
  }
  const result = new T.BufferGeometry();
  result.setAttribute("position", new T.Float32BufferAttribute(points, 3));
  result.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
  result.setAttribute("uv", new T.Float32BufferAttribute(uvs, 2));
  result.setIndex(indices);
  result.computeVertexNormals();
  return result;
}
