import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

type Point = [number, number, number];
const tau = 2 * Math.PI;

/** A pair of beast-faced bronze shoulder guards over a field of lacquer scales.
 * Local +Z faces the opponent; arm and wrist fittings have separate pivots. */
export function cinderArmour() {
  const cast = new T.MeshStandardMaterial({
    name: "Smoke-stained copper", vertexColors: true, metalness: 0.35, roughness: 0.57,
    side: T.DoubleSide,
  });
  const gold = new T.MeshStandardMaterial({
    name: "Rubbed bronze", color: 0xcdac72, metalness: 0.48, roughness: 0.44,
  });
  const shadow = new T.MeshStandardMaterial({
    name: "Black lacquer", color: 0x372b27, metalness: 0.29, roughness: 0.51,
  });
  const cloth = new T.MeshStandardMaterial({
    name: "Burnished cord", color: 0x743824, roughness: 0.82, side: T.DoubleSide,
  });
  const ivory = new T.MeshStandardMaterial({
    name: "Old ivory inlay", color: 0xb5a486, roughness: 0.60,
  });
  const piles = new Map<T.Material,T.BufferGeometry[]>();
  function add(mat: T.Material, geo: T.BufferGeometry) {
    const flat = geo.index ? geo.toNonIndexed() : geo;
    if (flat !== geo) geo.dispose();
    if (!piles.has(mat)) piles.set(mat, []);
    piles.get(mat)!.push(flat);
  }
  function finish(name: string) {
    const obj = new T.Group();
    obj.name = name;
    for (const [mat, geometries] of piles) {
      const mesh = new T.Mesh(mergeGeometries(geometries), mat);
      mesh.name = mat.name;
      mesh.castShadow = mesh.receiveShadow = true;
      obj.add(mesh);
      geometries.forEach(g => g.dispose());
    }
    piles.clear();
    return obj;
  }
  function wire(mat: T.Material, coords: Point[], radius: number, closed = false) {
    const path = new T.CatmullRomCurve3(coords.map(p => new T.Vector3(...p)), closed);
    add(mat, new T.TubeGeometry(path, Math.max(10, coords.length * 2), radius, 6, closed));
  }
  function boss(mat: T.Material, x: number, y: number, z: number, w: number, h: number, d: number) {
    add(mat, new T.SphereGeometry(1, 14, 9).scale(w,h,d).translate(x,y,z));
  }
  const shoulder = () => {
    // One continuous face, with hollows behind the brows and paired muzzle pads.
    const plate = new T.SphereGeometry(1, 76, 52);
    const pos = plate.attributes.position;
    const tint = new T.Color(), base = new T.Color(0xbb9368), patina = new T.Color(0x51625c);
    const colors = new Float32Array(pos.count * 3);
    const hill = (u: number, v: number, w: number, h: number) =>
      Math.exp(-((u/w)**2 + (v/h)**2));
    for (let i=0;i<pos.count;i++) {
      const u=pos.getX(i), v=pos.getY(i), z=pos.getZ(i), x=Math.abs(u);
      const face = T.MathUtils.smoothstep(z,0.05,0.55);
      const eye = hill(x-.42,v-.19,.24,.12);
      const muzzle = hill(x-.27,v+.20,.25,.24);
      const brow = hill(x-.40,v-.33-.14*x,.30,.12);
      const nose = hill(x,v-.01,.22,.32);
      const jaw = hill(x-.19,v+.55,.25,.14);
      const mane = Math.cos(25*x+7*v)*hill(x-.77,v+.11,.22,.65);
      const relief = .098*muzzle+.084*brow+.13*nose+.038*jaw-.054*eye+.017*mane;
      pos.setXYZ(i, u*(.318+.035*v), .285*v, .199*z+face*relief);
      const wear = .5+.5*Math.cos(40*u+17*v+Math.sin(31*z));
      tint.copy(base).lerp(patina,.17+.38*eye+.15*(1-wear))
        .multiplyScalar(.82+.17*wear+.21*brow+.20*muzzle);
      tint.toArray(colors,3*i);
    }
    plate.setAttribute("color", new T.BufferAttribute(colors,3));
    plate.computeVertexNormals();
    add(cast,plate);
    // Bossed cheeks, high spiralling brows, slit pupils and flared nostrils.
    for (const side of [-1,1]) {
      const line = (pts:Point[], r:number, mat:T.Material=gold) =>
        wire(mat,pts.map(([x,y,z]) => [side*x,y,z]),r);
      boss(shadow,side*.123,.047,.189,.058,.029,.028);
      boss(ivory,side*.121,.051,.212,.037,.014,.017);
      boss(shadow,side*.119,.051,.227,.009,.014,.006);
      line([[.032,.066,.256],[.075,.096,.246],[.141,.113,.224],[.204,.149,.172],[.207,.17,.146],[.184,.165,.149]],.012);
      line([[.074,.030,.221],[.124,.018,.212],[.171,.041,.192]],.008);
      boss(shadow,side*.045,-.018,.294,.024,.016,.015);
      line([[.011,-.068,.286],[.048,-.1,.264],[.103,-.094,.242],[.161,-.073,.203]],.009,shadow);
      line([[.108,-.089,.242],[.106,-.117,.242],[.097,-.141,.224]],.012,ivory);
      for(let curl=0;curl<3;curl++){
        const drop=.057*curl;
        line([[.178,.062-drop,.190],[.221,.075-drop,.154],[.251,.048-drop,.126],
          [.247,.018-drop,.117],[.218,.022-drop,.148]],.009);
      }
      line([[.02,.173,.173],[.058,.188,.166],[.091,.172,.173],[.094,.153,.187],[.073,.153,.189]],.008);
      line([[.14,.158,.163],[.178,.225,.132],[.221,.246,.066],[.239,.232,.036]],.017);
    }
    lineOfStuds();
    // Shingled lames below the repoussé face. Their shallow dishes catch firelight.
    for (let row=0;row<2;row++) {
      for(let i=0;i<5;i++) {
        const a=(i-2)*.56+(row===0?0:.12);
        const lx=.23*Math.sin(a), lz=.151*Math.cos(a);
        const scale=new T.SphereGeometry(1,16,10)
          .scale(.078,.097,.023).rotateY(a)
          .translate(lx,-.20-row*.088+.045*Math.abs(Math.sin(a)),lz);
        add(shadow,scale);
        const cy=-.20-row*.088+.045*Math.abs(Math.sin(a));
        wire(gold, [[lx-.042*Math.cos(a),cy-.037,lz+.013],[lx,cy-.079,lz+.020],
          [lx+.042*Math.cos(a),cy-.037,lz+.013]],.004);
        boss(gold,lx,cy+.016,lz+.024,.012,.011,.008);
      }
    }
    return finish("Lion shoulder and lacquered lames");
  };
  function lineOfStuds() {
    for(let i=0;i<13;i++) {
      const a=.2+(Math.PI-.4)*i/12;
      boss(gold,.287*Math.cos(a),.260*Math.sin(a),.080,.012,.012,.011);
    }
  }
  function cuff() {
    // The local Y axis runs along the forearm. A narrow back gap and paired
    // cord bindings let the casting taper towards the hand.
    const arc=(t:number,y:number,offset=0):Point=>{
      const a=-2.88+5.76*t, r=.125-.021*(y+.18)/.36+offset;
      return [Math.sin(a)*r*1.15,y,Math.cos(a)*r];
    };
    const g=new T.PlaneGeometry(1,1,40,14), pos=g.attributes.position, uv=g.attributes.uv;
    for(let i=0;i<pos.count;i++) {
      const t=uv.getX(i), y=(uv.getY(i)-.5)*.32;
      pos.setXYZ(i,...arc(t,y));
    }
    g.computeVertexNormals();
    shadow.side=T.DoubleSide;
    add(shadow,g);
    for(const y of [-.157,-.128,.11,.154]) {
      wire(gold,Array.from({length:33},(_,i)=>arc(i/32,y,.002)),.008);
    }
    for(let i=0;i<6;i++) {
      const t0=.075+i*.142;
      wire(gold,[arc(t0,.081,.003),arc(t0+.069,.004,.005),arc(t0,-.081,.003)],.005);
      boss(gold,...arc(t0,0,.008),.012,.013,.012);
    }
    for(let i=0;i<3;i++)
      wire(cloth,Array.from({length:24},(_,j)=>arc(j/23,-.165-.015*i+.011*j/23,.013)),.008);
    return finish("Bound forearm guard");
  }
  return ([-1,1] as const).map(side=>{
    const cap=shoulder(), bracer=cuff();
    cap.position.set(side*.555,2.875,-.392);
    cap.rotation.set(-.30,side*.25,-side*.11);
    bracer.position.set(side*1.032,2.532,.139);
    bracer.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),
      new T.Vector3(side*.42,-.055,.84).normalize());
    return {side,cap,bracer};
  });
}
