import * as T from "three";

/** A raised covered walk. Local +Z faces the court. Static pieces join the
 * existing court batches after the two wings are placed in world space. */
export function belfryGallery(bells: boolean, timber: T.Texture, rock: T.Texture,
  beam: T.Texture, procession: T.Texture, metal: T.MeshStandardMaterial) {
  const wing = new T.Group();
  wing.name = bells ? "Votive bell walk" : "River procession gallery";
  const pigment = (color: number, map: T.Texture | null = null) =>
    new T.MeshStandardMaterial({ color, map, roughness: .74 });
  const red = pigment(0xc48169, timber), green = pigment(0x568079);
  const ochre = pigment(0xc79c61), stone = pigment(0xadae9b, rock);
  const brown = pigment(0x876853, timber);
  const bronze = metal.clone();
  bronze.color.setHex(0xc9aa74);
  bronze.vertexColors = true;
  bronze.metalness = .61;
  bronze.roughness = .74;
  const raisedBronze = metal.clone();
  raisedBronze.color.setHex(0xc8a062);
  const beamPaint = new T.MeshStandardMaterial({ map: beam, emissiveMap: beam,
    emissive: 0xffead1, emissiveIntensity: .16, roughness: .75 });
  function put(geometry: T.BufferGeometry, material: T.Material, x: number, y: number, z: number) {
    const mesh = new T.Mesh(geometry, material);
    mesh.castShadow = mesh.receiveShadow = true;
    mesh.position.set(x,y,z);
    wing.add(mesh);
    return mesh;
  }
  function box(material: T.Material, x: number, y: number, z: number, w: number, h: number, d: number) {
    return put(new T.BoxGeometry(w,h,d),material,x,y,z);
  }
  function turned(points: number[][], sides: number) {
    return new T.LatheGeometry(points.map(([r,h]) => new T.Vector2(r,h)), sides);
  }
  function hangingBell(x: number, scale: number) {
    const top = 4.34, z = .22;
    const shell = turned([[.62,.06],[.72,0],[.74,.075],[.68,.15],[.62,.21],
      [.55,.61],[.535,.65],[.55,.69],[.52,.73],[.47,1.13],[.44,1.22],[.30,1.31],[.09,1.37],[.016,1.37]],32);
    const p = shell.attributes.position, colors = [], dye = new T.Color();
    for(let i=0;i<p.count;i++){
      const a = Math.atan2(p.getX(i),p.getZ(i)), h = p.getY(i);
      const patina = Math.max(0,Math.sin(7*a+1.3*h)*.45+Math.cos(11*a-3*h)*.22+.14);
      dye.setRGB(.96-.65*patina,.83-.20*patina,.66+.16*patina);
      colors.push(dye.r,dye.g,dye.b);
    }
    shell.setAttribute("color",new T.Float32BufferAttribute(colors,3));
    const foot = top-1.68*scale;
    put(shell.scale(scale,scale,scale),bronze,x,foot,z);
    // Cast borders catch the raking light around the darker engraved waist.
    for(const [radius,height] of [[.695,.14],[.562,.60],[.553,.72],[.454,1.18]]){
      const rim=new T.TorusGeometry(radius*scale,.023*scale,6,32).rotateX(Math.PI/2);
      put(rim,raisedBronze,x,foot+height*scale,z);
    }
    for(let j=0;j<6;j++){
      const a=j*Math.PI/3;
      const seal=new T.TorusGeometry(.115*scale,.025*scale,6,8);
      seal.scale(1,1.34,1).rotateX(-.14).rotateY(a);
      put(seal,raisedBronze,x+.50*scale*Math.sin(a),foot+.93*scale,z+.50*scale*Math.cos(a));
    }
    put(new T.TorusGeometry(.156*scale,.045*scale,8,18),ochre,x,foot+1.46*scale,z);
    box(brown,x,top-.075*scale,z,.084,.27*scale,.084);
    for(let i=0;i<10;i++){
      const a=i*Math.PI/5;
      put(new T.SphereGeometry(.048*scale,8,5),ochre,x+.555*scale*Math.sin(a),
        foot+.59*scale,z+.555*scale*Math.cos(a));
    }
    put(turned([[.015,-.18],[.10,-.12],[.12,-.04],[.06,.06],[.03,.48]],12)
      .scale(scale,scale,scale),brown,x,foot,z);
  }
  box(stone,0,.34,-.22,30.9,.68,3.95);
  box(stone,0,.66,-.20,31.1,.13,4.06);
  for (const x of [-10,0,10]) {
    for(let i=0;i<3;i++)box(stone,x,.1+i*.102,2.45-i*.29,3.2,.20+i*.205,.36);
  }
  for(let i=0;i<=6;i++){
    const x=-15+i*5;
    for(const z of [1.23,-1.7]){
      put(turned([[.39,0],[.38,.09],[.30,.14],[.32,.24],[.23,.36]],16),stone,x,.72,z);
      put(new T.CylinderGeometry(.19,.23,3.97,20),red,x,3.05,z);
      box(red,x,5.02,z,.55,.23,.51);
      for(const sign of [-1,1]){
        box(green,x+sign*.34,5.23,z+.05,.82,.22,.31).rotation.z=sign*.28;
        box(ochre,x+sign*.59,5.42,z+.09,.30,.12,.37);
      }
      box(green,x,5.55,z+.14,1.77,.20,.45);
    }
    box(brown,x,5.70,-.06,.26,.30,4.5);
  }
  for(let i=0;i<6;i++){
    const x = -12.5+i*5;
    box(brown,x,5.85,1.40,5.04,.32,1.48);
    box(red,x,5.73,1.67,5.04,.16,.27);
    box(green,x,5.07,1.21,4.85,.52,.31);
    put(new T.PlaneGeometry(4.64,.49),beamPaint,x,5.07,1.372);
    for(const y of [4.79,5.35])box(ochre,x,y,1.27,4.87,.05,.29);
    for(let j=0;j<9;j++){
      const rx=x+(j-4)*.54;
      box(brown,rx,5.75,1.57,.145,.16,1.40).rotation.x=.13;
      box(ochre,rx,5.66,2.25,.15,.15,.075);
    }
    // Low balustrades leave three stair openings along the front edge.
    box(red,x,1.55,1.50,1.82,.14,.15);
    for(const dx of [-.83,-.42,0,.42,.83])box(green,x+dx,1.14,1.50,.09,.77,.10);
    if(bells){
      box(brown,x,4.45,.22,5.06,.22,.25);
      for(const sign of [-1,1])box(red,x+sign*2.10,4.75,.22,.13,.83,.15).rotation.z=-sign*.64;
      hangingBell(x, [.84,1.16,1.51,1.30,1.08,.94][i]);
      if(i===2 || i===3)hangingBell(x+1.53,.66);
    }
  }
  if(!bells){
    // The mural has one continuous 3:1 composition across three central bays.
    const plaster = new T.MeshStandardMaterial({ map: procession, emissiveMap: procession,
      emissive: 0xffe6c2, emissiveIntensity: .29, roughness: .94 });
    box(brown,0,2.95,-1.86,15.1,4.65,.18);
    put(new T.PlaneGeometry(14.8,4.49),plaster,0,2.95,-1.76);
    for(const y of [.72,5.18])box(ochre,0,y,-1.70,14.95,.10,.15);
    for(const side of [-1,1]){
      // Open octagonal windows at each end reveal the mountains beyond.
      for(const cx of [9.45,13]){
        const x = side*cx;
        for(let n=0;n<8;n++){
          const a=n*Math.PI/4;
          box(red,x+1.43*Math.sin(a),2.96+1.43*Math.cos(a),-.86,
            1.24,.17,.24).rotation.z=-a;
        }
        for(const sign of [-1,1]){
          box(green,x+sign*1.47,2.97,-.87,.105,4.15,.14);
          box(ochre,x,2.96+sign*1.68,-.87,3.0,.085,.16);
        }
      }
    }
  }
  return wing;
}
