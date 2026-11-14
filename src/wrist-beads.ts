import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** A suspended loop on the casting cuff. The carved seed beads and brass
 * spacers follow a common silk cord; its tassel hangs below the guru bead. */
export class WristBeads extends T.Group {
  private last = new T.Vector3();
  private velocity = new T.Vector3();
  private support = new T.Vector3();
  private direction = new T.Vector3();
  private swing = new T.Vector2();
  private speed = new T.Vector2();
  private ready = false;

  constructor() {
    super();
    this.name = "Saint's votive beads";
    const pieces: T.BufferGeometry[] = [];
    const cinnabar = new T.Color(0x903e27), seed = new T.Color(0x673322);
    const aged = new T.Color(0xbd904d), cord = new T.Color(0x49271e);
    const tint = new T.Color();
    const add = (g: T.BufferGeometry, c: T.Color) => {
      const n = g.getAttribute("position").count, rgb = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) c.toArray(rgb, i * 3);
      g.setAttribute("color", new T.BufferAttribute(rgb, 3));
      pieces.push(g);
    };
    const ball = (p: T.Vector3, size: number, c: T.Color) =>
      add(new T.SphereGeometry(size, 12, 8).scale(1, .90, .96).translate(p.x,p.y,p.z), c);
    const curve = new T.CatmullRomCurve3([
      new T.Vector3(-.048,.015,0),new T.Vector3(-.12,-.19,.018),
      new T.Vector3(-.084,-.36,.042),new T.Vector3(.014,-.407,.052),
      new T.Vector3(.105,-.32,.038),new T.Vector3(.105,-.16,.015),new T.Vector3(.05,.015,0),
    ]);
    add(new T.TubeGeometry(curve,36,.007,6,false), cord);
    for (let i=0; i<20; i++) {
      const p = curve.getPointAt((i+.5)/20);
      const gold = i%5===2;
      ball(p, gold ? .020 : .029, gold ? aged : tint.copy(seed).lerp(cinnabar,.5+.4*Math.cos(i*3.1)));
    }
    ball(new T.Vector3(.013,-.438,.052),.037,aged);
    for(let j=0;j<8;j++){
      const t=j*Math.PI/4, x=Math.cos(t), z=Math.sin(t);
      const strand = new T.CatmullRomCurve3([
        new T.Vector3(.013,-.456,.052), new T.Vector3(.013+x*.022,-.501,.052+z*.019),
        new T.Vector3(.022+x*.033,-.602-.023*Math.cos(j*7),.060+z*.028),
      ]);
      add(new T.TubeGeometry(strand,6,.007,5,false), tint.copy(cinnabar).multiplyScalar(.8+.26*Math.sin(t)));
    }
    const mesh = new T.Mesh(mergeGeometries(pieces),
      new T.MeshStandardMaterial({vertexColors:true,metalness:.23,roughness:.49}));
    mesh.castShadow = mesh.receiveShadow = true;
    this.add(mesh);
    pieces.forEach(g=>g.dispose());
  }

  follow(hand: T.Bone, fore: T.Bone, root: T.Group, dt: number) {
    hand.getWorldPosition(this.support);
    fore.getWorldPosition(this.direction).sub(this.support).normalize();
    this.support.addScaledVector(this.direction,.11);
    root.worldToLocal(this.support);
    // Root space keeps the string hanging vertically as the wrist turns.
    this.position.copy(this.support);
    if (!this.ready || dt <= 0 || dt > .1 || this.support.distanceToSquared(this.last) > .35) {
      this.swing.set(0,0);
      this.speed.set(0,0);
      this.velocity.set(0,0,0);
      this.ready=true;
    } else {
      this.direction.copy(this.support).sub(this.last).multiplyScalar(1/dt);
      const ax = T.MathUtils.clamp((this.direction.x-this.velocity.x)/dt,-32,32);
      const az = T.MathUtils.clamp((this.direction.z-this.velocity.z)/dt,-32,32);
      const count=Math.ceil(dt*120), step=dt/count;
      for(let i=0;i<count;i++){
        this.speed.x += (-az*.88 - 22*Math.sin(this.swing.x)-4.5*this.speed.x)*step;
        this.speed.y += (-ax*.88 - 22*Math.sin(this.swing.y)-4.5*this.speed.y)*step;
        this.swing.addScaledVector(this.speed,step);
      }
      this.velocity.copy(this.direction);
    }
    this.last.copy(this.support);
    this.rotation.set(-this.swing.x,.28,this.swing.y);
  }
}
