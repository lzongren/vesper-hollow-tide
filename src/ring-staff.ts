import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

function turned(profile: number[][]) {
  return new T.LatheGeometry(profile.map(([r, y]) => new T.Vector2(r, y)), 28);
}

function wire(points: number[][], radius: number) {
  const path = new T.CatmullRomCurve3(points.map(([x, y, z]) => new T.Vector3(x, y, z)));
  return new T.TubeGeometry(path, 26, radius, 8, false);
}

/** Lacquered pilgrim's staff with an open bronze finial. Three loose rings
 * thread each side rail; the voids keep the silhouette legible against fire. */
export class RingStaff extends T.Group {
  private pendants: T.Mesh[] = [];
  private swing = 0;
  private velocity = 0;
  private previousTilt?: number;

  constructor(wood: T.Material, bronze: T.Material, binding: T.Material, ember: T.Material) {
    super();
    const fittings: T.BufferGeometry[] = [];
    const add = (geometry: T.BufferGeometry, material: T.Material) => {
      const mesh = new T.Mesh(geometry, material);
      mesh.castShadow = mesh.receiveShadow = true;
      this.add(mesh);
      return mesh;
    };
    add(turned([[.019,-.52],[.034,-.49],[.037,.11],[.032,1.83],[.042,1.94]]), wood);
    add(turned([[.035,-.19],[.045,-.16],[.043,.18],[.034,.20]]), binding);
    for (const y of [-.49,-.21,.18,1.72,1.84]) {
      fittings.push(turned([[.036,y],[.049,y+.018],[.047,y+.043],[.033,y+.055]]));
    }
    // Flattened lotus socket: the petals overlap a turned ferrule and return
    // to the shaft beneath the two separate outward-curving bronze rails.
    fittings.push(turned([[.035,1.89],[.077,1.95],[.105,2.01],[.081,2.07],[.044,2.10]]));
    for (let i=0;i<7;i++) {
      const petal=new T.SphereGeometry(1,12,8).scale(.041,.084,.016);
      petal.rotateX(.43).translate(0,2.035,.083).rotateY(i*2*Math.PI/7);
      fittings.push(petal);
    }
    for (const side of [-1,1]) {
      const rail = (p: number[][], r: number) => fittings.push(wire(
        p.map(([x,y,z])=>[side*x,y,z]), r));
      rail([[.036,2.04,0],[.14,2.17,.01],[.295,2.31,.018],[.306,2.54,0],
            [.19,2.73,-.014],[.086,2.83,0],[0,3.03,0]],.025);
      rail([[.06,2.09,.002],[.105,2.29,.027],[.207,2.47,.018],[.179,2.61,.004],
            [.099,2.64,0],[.072,2.57,-.008],[.114,2.54,-.006]],.016);
      rail([[.18,2.72,0],[.237,2.82,-.013],[.202,2.93,-.012],[.123,3.005,0]],.014);
      // Each ring hangs below a different point on the sloped rail.
      for (let j=0;j<3;j++) {
        const radius=.103-.008*j;
        const ring = add(new T.TorusGeometry(radius,.012,8,34).translate(0,-radius,0), bronze);
        ring.position.set(side*(.229+.034*j),2.26+.05*j,.017);
        ring.rotation.y=side*(.6+.30*j);
        this.pendants.push(ring);
      }
    }
    fittings.push(turned([[.028,2.10],[.023,2.30],[.039,2.38],[.016,2.48]]));
    const merged=mergeGeometries(fittings);
    add(merged,bronze);
    fittings.forEach(part=>part.dispose());
    add(new T.OctahedronGeometry(.058,1).scale(.70,1.85,.70).translate(0,2.43,0),ember);
  }

  update(tilt: number, dt: number) {
    if (this.previousTilt === undefined || dt <= 0 || dt > .10) {
      this.swing=0;
      this.velocity=0;
    } else {
      const speed=T.MathUtils.clamp((tilt-this.previousTilt)/dt,-10,10);
      const target=T.MathUtils.clamp(-tilt*.48-speed*.045,-.75,.75);
      const steps=Math.ceil(dt*120), h=dt/steps;
      for (let i=0;i<steps;i++) {
        this.velocity+=((target-this.swing)*92-this.velocity*6)*h;
        this.swing+=this.velocity*h;
      }
    }
    this.previousTilt=tilt;
    this.pendants.forEach((ring,i)=>{
      ring.rotation.x=this.swing*(.82+.08*(i%3));
    });
  }
}
