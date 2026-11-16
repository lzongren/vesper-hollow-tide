import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** A votive path on the west face. Each bent rests on the cliff at two
 * surveyed heights; the outside stringer carries the deck above the gorge. */
export function cliffWalk(edge: T.Vector3[], feet: T.Vector3[]) {
  const root = new T.Group();
  root.name = "West cliff votive path";
  const material = new T.MeshStandardMaterial({ vertexColors: true, roughness: 0.86 });
  const parts: T.BufferGeometry[] = [], lamps: T.BufferGeometry[] = [];
  const wood = new T.Color(0x815c40), red = new T.Color(0x97563d);
  const tile = new T.Color(0x404e50), stone = new T.Color(0x838179);
  const grain = new T.Color(), axis = new T.Vector3(0, 1, 0);
  const outward = edge.map((p, i) => {
    const d = edge[Math.min(edge.length - 1, i + 1)].clone().sub(edge[Math.max(i - 1, 0)]);
    return new T.Vector3(d.z, 0, -d.x).normalize();
  });
  const last = edge.length - 1;
  function point(i: number, reach: number, lift = 0) {
    const turn = Math.max(0, 1 - Math.min(i, last - i) / 2);
    const p = edge[i].clone().addScaledVector(outward[i], reach - 2.05 * turn);
    p.y += lift;
    return p;
  }
  function beam(a: T.Vector3, b: T.Vector3, width: number, depth: number, tint: T.Color) {
    const d = b.clone().sub(a);
    const geom = new T.BoxGeometry(width, d.length(), depth);
    geom.applyQuaternion(new T.Quaternion().setFromUnitVectors(axis, d.normalize()));
    const middle = a.clone().lerp(b, 0.5);
    geom.translate(middle.x, middle.y, middle.z);
    const count = geom.getAttribute("position").count;
    const colors = new Float32Array(count * 3);
    for (let j = 0; j < count; j++) tint.toArray(colors, j * 3);
    geom.setAttribute("color", new T.BufferAttribute(colors, 3));
    parts.push(geom);
  }
  function panel(a: T.Vector3, b: T.Vector3, c: T.Vector3, d: T.Vector3, tint: T.Color) {
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.Float32BufferAttribute([a,b,c,d].flatMap(p => p.toArray()),3));
    g.setAttribute("color", new T.Float32BufferAttribute([0,1,2,3].flatMap(() => tint.toArray()),3));
    g.setIndex([0,1,2,0,2,3]);
    g.computeVertexNormals();
    parts.push(g);
  }
  for (let i = 0; i <= last; i++) {
    const outer = point(i, 2.05);
    beam(feet[i], outer, 0.18, 0.22, wood);
    beam(point(i, -0.48), point(i, 2.23), 0.22, 0.23, wood);
    beam(outer, point(i, 2.05, 1.18), 0.13, 0.13, red);
    if (i === last) break;
    beam(outer, point(i+1, 2.05), 0.2, 0.22, wood);
    for (const h of [0.56, 1.03]) beam(point(i, 2.05, h), point(i+1, 2.05, h), 0.09, 0.11, red);
    const boards = Math.ceil(edge[i].distanceTo(edge[i+1]) / 0.29);
    for (let k = 0; k < boards; k++) {
      const u = (k + 0.025) / boards, v = (k + 0.975) / boards;
      const plank = (reach: number, t: number) =>
        point(i, reach, 0.12).lerp(point(i + 1, reach, 0.12), t);
      grain.copy(wood).multiplyScalar(0.82 + 0.18 * Math.cos(7 * k + i));
      panel(plank(-0.52,u), plank(-0.52,v), plank(2.16,v), plank(2.16,u), grain);
    }
  }
  // Two sheltered bays. The curved eave deepens in the centre and kicks
  // upwards at the ends. Lamp and roof are visible from below.
  const start = 2, finish = start + 2;
  for (let i = start; i <= finish; i++) {
    for (const reach of [-0.18, 2.05]) {
      beam(point(i, reach), point(i, reach, 2.52), 0.19, 0.19, red);
      beam(point(i, reach, 2.25), point(i, reach + 0.4, 2.52), 0.11, 0.12, wood);
    }
    if (i === finish) continue;
    const roof = (bay: number, reach: number) => {
      const eave = Math.abs(reach - 0.85) / 1.7;
      return point(bay, reach, 3.47 - 0.88 * Math.sin(eave * 1.57) +
        (bay === start || bay === finish ? 0.39 * eave ** 3 : 0));
    };
    for (let course = 0; course < 10; course++) {
      const a = -0.85 + 0.34 * course, b = a + 0.34;
      panel(roof(i,a),roof(i+1,a),roof(i+1,b),roof(i,b), tile);
    }
    beam(roof(i,0.85),roof(i+1,0.85), 0.16, 0.16, stone);
    const lamp = point(i, 1.52, 1.91).lerp(point(i+1, 1.52, 1.91), .5);
    beam(lamp, lamp.clone().addScaledVector(axis, .82), .034, .035, wood);
    const globe = new T.SphereGeometry(.24, 12, 8).scale(.87, 1.27, .87);
    globe.translate(lamp.x, lamp.y, lamp.z);
    lamps.push(globe);
  }
  function mesh(geos: T.BufferGeometry[], mat: T.Material) {
    for (const g of geos) g.deleteAttribute("uv");
    const m = new T.Mesh(mergeGeometries(geos), mat);
    m.castShadow = m.receiveShadow = true;
    root.add(m);
    geos.forEach(g => g.dispose());
  }
  material.side = T.DoubleSide;
  mesh(parts, material);
  mesh(lamps, new T.MeshStandardMaterial({color:0xffd291,emissive:0xffb05d,emissiveIntensity:2.2}));
  return root;
}
