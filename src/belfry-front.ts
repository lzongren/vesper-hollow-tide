import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** A timber front with projecting bracket sets and two banks of folding screens.
 * Coordinates are in the existing hall's local frame. */
export function belfryFront(beamMap: T.Texture, paperMap: T.Texture, timberMap: T.Texture, stoneMap: T.Texture) {
  function pigment(name: string, color: number, roughness: number, map?: T.Texture) {
    return new T.MeshStandardMaterial({ name, color, roughness, map: map ?? null });
  }
  const red = pigment("Oxide-red posts",0xb56b49,.72,timberMap);
  const cream = pigment("Worn ochre on cut edges",0xbd9b63,.63);
  const teal = pigment("Mineral green bracket ends",0x51827a,.72);
  const blue = pigment("Indigo soffit",0x425969,.81);
  const dark = pigment("Smoked timber",0x815a48,.80,timberMap);
  const stone = pigment("Carved column plinth",0xafb2a2,.88,stoneMap);
  const painted = new T.MeshStandardMaterial({
    name:"Paired dragons on the tie beam",map:beamMap,
    roughness:.71, emissiveMap:beamMap, emissive:0xffffff, emissiveIntensity:.11,
  });
  const paper = new T.MeshStandardMaterial({
    name:"Lit mulberry paper",vertexColors:true,color:0xe7d6ab,roughness:.94,
    map:paperMap,emissive:0xd4b586,emissiveMap:paperMap,emissiveIntensity:.58,
  });
  const group = new T.Group(), piles = new Map<T.Material,T.BufferGeometry[]>();
  group.name="Painted belfry threshold";
  function add(mat: T.Material, input: T.BufferGeometry) {
    const g=input.index?input.toNonIndexed():input;
    if(g!==input)input.dispose();
    if(!piles.has(mat))piles.set(mat,[]);
    piles.get(mat)!.push(g);
  }
  function box(mat:T.Material,x:number,y:number,z:number,w:number,h:number,d:number) {
    add(mat,new T.BoxGeometry(w,h,d).translate(x,y,z));
  }
  function bar(mat:T.Material,a:T.Vector3,b:T.Vector3,w:number,d:number) {
    const delta=b.clone().sub(a);
    const rot=new T.Quaternion().setFromUnitVectors(new T.Vector3(0,1,0),delta.clone().normalize());
    add(mat,new T.BoxGeometry(w,delta.length(),d).applyQuaternion(rot)
      .translate((a.x+b.x)*.5,(a.y+b.y)*.5,(a.z+b.z)*.5));
  }
  // Carved cantilevers have a flat bearing face and a stepped, rounded lower edge.
  function arm(x:number,y:number,z:number,length:number,alongZ:boolean,mat:T.Material) {
    const h=.145, half=length/2, s=new T.Shape();
    s.moveTo(-half,h);s.lineTo(half,h);s.lineTo(half,.044);
    s.quadraticCurveTo(half-.09,.055,half-.12,-.024);
    s.quadraticCurveTo(half-.16,-.083,half-.29,-.070);
    s.lineTo(.19,-h);s.lineTo(-.19,-h);s.lineTo(-half+.29,-.07);
    s.quadraticCurveTo(-half+.15,-.082,-half+.12,-.024);
    s.quadraticCurveTo(-half+.09,.052,-half,.044);s.closePath();
    const g=new T.ExtrudeGeometry(s,{depth:.21,bevelEnabled:false,curveSegments:4});
    g.translate(0,0,-.105);
    if(alongZ)g.rotateY(Math.PI/2);
    add(mat,g.translate(x,y,z));
  }
  function paintedBeam(x:number,y:number,z:number,w:number,h:number) {
    box(dark,x,y,z-.10,w+.05,h+.09,.20);
    add(painted,new T.PlaneGeometry(w,h).translate(x,y,z+.006));
    for(const sign of [-1,1])box(cream,x,y+sign*(h/2+.012),z,w+.08,.027,.06);
  }
  function bracket(x:number,base:number,z:number,scale:number) {
    const y=base;
    box(red,x,y,z,.46,.19,.46);
    arm(x,y+.17,z,1.09,false,teal);
    for(const side of [-1,1]){
      box(cream,x+side*.39,y+.32,z,.23,.10,.28);
      box(teal,x+side*.39,y+.40,z,.31,.09,.34);
      arm(x+side*.36,y+.50,z+.06,.83,true,red);
      box(cream,x+side*.36,y+.63,z+.36,.25,.09,.21);
    }
    arm(x,y+.67,z+.26,1.72*scale,false,teal);
    for(const side of [-1,1]){
      box(blue,x+side*.62*scale,y+.82,z+.26,.32,.12,.38);
      box(cream,x+side*.62*scale,y+.90,z+.26,.39,.055,.39);
    }
  }
  for(const x of [-5.04,-2.50,2.50,5.04]){
    const plinth=new T.LatheGeometry([
      new T.Vector2(.39,0),new T.Vector2(.40,.08),new T.Vector2(.33,.14),
      new T.Vector2(.36,.21),new T.Vector2(.31,.32),new T.Vector2(.265,.37),
    ],24);
    add(stone,plinth.translate(x,1.10,2.65));
    add(red,new T.CylinderGeometry(.226,.252,3.26,24).translate(x,3.07,2.65));
    for(const y of [1.49,4.42])add(cream,new T.CylinderGeometry(.255,.256,.055,24).translate(x,y,2.65));
    bracket(x,4.60,2.83,1);
  }
  for(const side of [-1,1]){
    // Paired dragons fill a bay. The timber relief casts across its painted face.
    paintedBeam(side*3.92,4.81,3.17,2.44,.56);
    paintedBeam(side*3.85,5.53,3.52,3.13,.36);
    const mid=side*3.79, frameZ=2.63, width=1.93;
    for(let panel=0;panel<3;panel++){
      const x=mid + (panel-1)*.657, bottom=1.45;
      const cg=new T.PlaneGeometry(.596,2.14,8,16);
      const uv=cg.attributes.uv;
      for(let i=0;i<uv.count;i++)uv.setXY(i,(uv.getX(i)+panel)/3,uv.getY(i));
      const pos=cg.attributes.position, color=new T.Color(), col:number[]=[];
      for(let i=0;i<pos.count;i++){
        const u=pos.getX(i),v=pos.getY(i);
        const dye=.52+.35*Math.exp(-((u-.16*side)**2*6+(v+.32)**2*1.6))+.055*Math.sin(v*47+panel*3+u*19);
        color.setRGB(dye,.85*dye,.65*dye);col.push(color.r,color.g,color.b);
      }
      cg.setAttribute("color",new T.Float32BufferAttribute(col,3));
      add(paper,cg.translate(x,bottom+1.68,frameZ-.102));
      for(const sign of [-1,1]){
        box(red,x+sign*.313,bottom+1.40,frameZ,.058,2.86,.11);
        box(dark,x,bottom+1.67+sign*1.08,frameZ,.60,.064,.12);
      }
      // A fretted top and bottom, with a central octagon in the long light.
      for(const h of [.77,2.56]){
        box(dark,x,bottom+h,frameZ,.63,.034,.072);
        for(const dx of [-.179,0,.179])box(dark,x+dx,bottom+h+(h<1?-.075:.075),frameZ,.024,.17,.066);
      }
      for(const dx of [-.195,.195]){
        box(dark,x+dx,bottom+1.32,frameZ,.028,1.04,.08);
        box(dark,x+dx,bottom+2.22,frameZ,.028,.63,.08);
      }
      const points=Array.from({length:8},(_,i)=>{
        const a=Math.PI*(i+.5)/4;
        return new T.Vector3(x+Math.sin(a)*.216,bottom+1.72+Math.cos(a)*.255,frameZ+.013);
      });
      for(let i=0;i<8;i++)bar(cream,points[i],points[(i+1)%8],.026,.06);
      box(red,x,bottom+.28,frameZ,.60,.52,.10);
      box(dark,x,bottom+.28,frameZ+.064,.48,.39,.035);
      box(teal,x,bottom+.28,frameZ+.087,.41,.32,.017);
    }
    box(dark,mid,1.32,frameZ,width+.19,.19,.35);
    box(cream,mid,4.40,frameZ,width+.18,.071,.24);
    // Carved stone returns frame the stair. Balusters sit in timber-sized
    // mortises between the paving and handrail, with a small lotus finial.
    const first=new T.Vector3(side*3.46,.89,5.05), last=new T.Vector3(side*3.46,1.79,2.05);
    bar(stone,first,last,.20,.24);
    for(let i=0;i<=4;i++){
      const t=i/4, x=first.x, z=T.MathUtils.lerp(first.z,last.z,t), y=T.MathUtils.lerp(first.y,last.y,t);
      const post=new T.LatheGeometry([new T.Vector2(.19,-.86),new T.Vector2(.19,-.68),
        new T.Vector2(.128,-.62),new T.Vector2(.11,-.19),new T.Vector2(.163,-.13),
        new T.Vector2(.147,.10),new T.Vector2(.11,.14)],12);
      add(stone,post.translate(x,y,z));
      if(i===0||i===4){
        const bud=new T.LatheGeometry([new T.Vector2(.076,.10),new T.Vector2(.135,.19),
          new T.Vector2(.111,.27),new T.Vector2(.03,.37),new T.Vector2(.006,.39)],12);
        add(stone,bud.translate(x,y,z));
      }
    }
  }
  // A side lintel is thinner than the central plaque and lies behind its face.
  paintedBeam(0,5.58,3.06,3.87,.20);
  // Parallel exposed rafter tails under the lifted front roof corners.
  for(let i=-29;i<=29;i++){
    const x=i*.231, rise=.65*(Math.abs(x)/7)**7;
    const start=new T.Vector3(x,6.03+rise,2.83),end=new T.Vector3(x,5.86+rise,4.03);
    bar(red,start,end,.109,.14);
    box(cream,x,end.y,end.z+.012,.116,.127,.043);
  }
  for(const [material,list] of piles){
    const merged=mergeGeometries(list);
    const m=new T.Mesh(merged,material);
    m.name=material.name;m.castShadow=true;m.receiveShadow=true;
    group.add(m);list.forEach(g=>g.dispose());
  }
  return group;
}
