import * as T from "three";
import type { Hazard } from "./combat";

/** Eight vents can coexist in the awakened cast. Keep their lights in the
 * shrine throughout the encounter so the ignition cannot change shader variants. */
export class CinderLights extends T.Group {
  private sources = Array.from({ length: 8 }, () => new T.PointLight(0xffab69, 0, 9.5, 2));

  constructor() {
    super();
    this.add(...this.sources);
  }

  update(hazards: readonly Hazard[]) {
    let slot = 0;
    for (const h of hazards) {
      if (h.type !== "eruption" || slot >= this.sources.length) continue;
      const lamp = this.sources[slot++];
      const age = h.age - h.delay;
      const duration = h.life - h.delay;
      const rise = T.MathUtils.smoothstep(age, 0, .15);
      const fade = 1 - T.MathUtils.smoothstep(age, duration - .26, duration);
      const flicker = 1 + .07 * Math.sin(age * 18 + h.id) + .035 * Math.sin(age * 31 - h.id);
      lamp.position.set(h.x, .36 + .88 * rise * fade, h.z);
      lamp.intensity = 43 * rise * fade * flicker;
    }
    for (; slot < this.sources.length; slot++) this.sources[slot].intensity = 0;
  }
}


const cell = new T.Vector3(40, 52, 40);
const framesPerRow = 4;
const variations = 2;

export async function shrineFireVolume() {
  const response = await fetch(`${import.meta.env.BASE_URL}textures/shrine-fire.rg8.gz`);
  if (!response.ok || !response.body) throw new Error("Could not load shrine fire");
  const raw = await new Response(response.body.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
  const width = cell.x * framesPerRow, height = cell.y * framesPerRow, depth = cell.z * variations;
  if (raw.byteLength !== width * height * depth * 2) throw new Error("Incomplete shrine fire volume");
  const map = new T.Data3DTexture(new Uint8Array(raw), width, height, depth);
  map.name = "Shrine fire temperature and smoke";
  map.format = T.RGFormat;
  map.minFilter = map.magFilter = T.LinearFilter;
  map.needsUpdate = true;
  // A small periodic lattice breaks up sub-voxel eddies where a tongue mixes
  // with cool air. Use hardware trilinear filtering for each octave.
  const noiseSize=32, bytes=new Uint8Array(noiseSize**3 * 4);
  let state=19317;
  for (let i=0;i<bytes.length;i++) {
    state=(Math.imul(state,1664525)+1013904223)>>>0;
    bytes[i]=state>>>24;
  }
  const eddies=new T.Data3DTexture(bytes,noiseSize,noiseSize,noiseSize);
  eddies.format=T.RGBAFormat;
  eddies.minFilter=eddies.magFilter=T.LinearFilter;
  eddies.wrapS=eddies.wrapT=eddies.wrapR=T.RepeatWrapping;
  eddies.needsUpdate=true;
  return {map,eddies};
}

/** Camera-aligned slices reconstruct the baked volume in court space, including
 * the planar reflection. Each slice is depth tested against the fighters. */
export class CinderFire extends T.Mesh<T.BufferGeometry, T.ShaderMaterial> {
  constructor(id: number, volume: Awaited<ReturnType<typeof shrineFireVolume>>) {
    const positions: number[] = [], kinds: number[] = [], indices: number[] = [];
    function quad(kind: number, layer: number) {
      const start = positions.length / 3;
      for (const [x, y] of [[-1,0],[1,0],[1,1],[-1,1]]) {
        positions.push(x,y,layer);
        kinds.push(kind);
      }
      indices.push(start,start+1,start+2,start,start+2,start+3);
    }
    quad(0,0); // Preheated fissures lie on the exposed stone under the burst.
    const slices = 14;
    for (let i=0;i<slices;i++) quad(1,((i+.5)/slices)*2-1);
    for (let i=0;i<27;i++) quad(i<9 ? 3 : 2,i);
    const geometry=new T.BufferGeometry();
    geometry.setAttribute("position",new T.Float32BufferAttribute(positions,3));
    geometry.setAttribute("kind",new T.Float32BufferAttribute(kinds,1));
    geometry.setIndex(indices);
    // Vertex positions encode slice and particle coordinates, not world bounds.
    geometry.boundingSphere=new T.Sphere(new T.Vector3(0,2,0),3);
    const material=new T.ShaderMaterial({
      glslVersion:T.GLSL3, transparent:true, side:T.DoubleSide, forceSinglePass:true, depthWrite:false,
      uniforms:{ field:{value:volume.map}, eddies:{value:volume.eddies}, seed:{value:id}, age:{value:-2}, life:{value:.85},
        eyeLocal:{value:new T.Vector3()}, cellSize:{value:cell} },
      vertexShader:`
        uniform float age,life,seed;uniform vec3 eyeLocal;
        in float kind;out vec3 samplePoint;out vec2 coord;flat out float surface;
        float hash(float n){return fract(sin(n*17.31+seed*23.47)*4375.13);}
        void main(){
          surface=kind;coord=position.xy;samplePoint=vec3(0.);
          vec2 front=normalize(eyeLocal.xz+vec2(.00001)),right=vec2(front.y,-front.x);
          vec3 p;
          if(kind<.5){
            p=vec3(position.x,.008,position.y*2.-1.);
          }else if(kind<1.5){
            vec2 slice=right*position.x+front*position.z;
            float angle=seed*2.39996;
            vec2 uv=mat2(cos(angle),sin(angle),-sin(angle),cos(angle))*slice;
            samplePoint=vec3(.5+.56*uv.x,position.y,.5+.56*uv.y);
            float height=mix(3.25,4.75,hash(2.));
            p=vec3(slice.x,position.y*height,slice.y);
          }else{
            float i=position.z,flight=clamp((age-.06-.34*hash(i+8.))/.65,0.,1.);
            float angle=6.283185*hash(i+.5),r=.10+flight*(.18+.51*hash(i+2.));
            vec2 travel=vec2(cos(angle),sin(angle))*r+vec2(.16,.03)*flight*flight;
            float y=.26+flight*(1.1+3.3*hash(i+3.))-1.35*flight*flight;
            float width=(kind>2.5 ? .027+.021*hash(i+4.) : .003+.007*hash(i+4.))*sin(3.14159*flight);
            if(kind>2.5){
              float twist=angle+flight*(5.+6.*hash(i+7.));
              travel+=front*position.x*width*sin(twist);
              width*=.16+.84*abs(cos(twist));
              travel+=right*(position.y-.5)*sin(twist*.7)*.068;
              y+=(position.y-.5)*(.105+.055*hash(i+10.))*sin(3.14159*flight);
            }
            travel+=right*position.x*width;
            p=vec3(travel.x,y+(kind<2.5 ? (position.y-.5)*width*10. : 0.),travel.y);
            samplePoint.y=flight;
          }
          gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);
        }`,
      fragmentShader:`
        precision highp sampler3D;
        uniform sampler3D field,eddies; uniform float seed,age,life; uniform vec3 cellSize;
        in vec2 coord;in vec3 samplePoint;flat in float surface;
        out vec4 flameColor;
        vec2 lookup(vec3 p,float frame){
          vec3 tile=vec3(mod(frame,4.),floor(frame/4.),mod(seed,2.));
          return texture(field,(tile*cellSize+.5+p*(cellSize-1.))/(cellSize*vec3(4.,4.,2.))).rg;
        }
        void main(){
          vec3 color;float alpha;
          if(surface<.5){
            vec2 p=vec2(coord.x,coord.y*2.-1.);
            float r=length(p),a=atan(p.y,p.x);
            float heat=smoothstep(-.8,0.,age)*(1.-smoothstep(.36,life,age));
            float vein=abs(sin(5.*a+seed+.6*sin(11.*r+seed)+.35*sin(13.*a-9.*r)));
            float cracks=1.-smoothstep(.018,.14,vein);
            float charred=1.-smoothstep(.36,.95,r+.06*cos(a*7.));
            color=mix(vec3(.055,.026,.018),vec3(1.9,.44,.052),cracks*heat);
            alpha=charred*heat*(.27+.65*cracks);
          }else if(surface<1.5){
            if(age<0.||any(lessThan(samplePoint,vec3(0.)))||any(greaterThan(samplePoint,vec3(1.))))discard;
            float t=clamp(age/life,0.,1.)*15.;
            vec3 p=samplePoint;
            vec3 flow=p*vec3(.28,.31,.28)+vec3(seed*.093,-age*.31,seed*.075);
            vec3 vortex=texture(eddies,flow*.61).rgb-.5;
            vec4 curls=texture(eddies,flow+vortex*.085);
            float fine=texture(eddies,flow*2.73+vortex*.111).r;
            float roll=.18+.82*smoothstep(0.,.42,p.y);
            p+=roll*(vortex*.14+(curls.rgb-.5)*.052);
            if(any(lessThan(p,vec3(0.)))||any(greaterThan(p,vec3(1.))))discard;
            vec2 f=mix(lookup(p,floor(t)),lookup(p,min(floor(t)+1.,15.)),fract(t));
            float turbulence=.64*curls.a+.36*fine;
            float fuel=f.x*(.84+.42*turbulence);
            float shell=smoothstep(.045,.12,fuel-.13*turbulence);
            float hot=shell*smoothstep(.031,.83,fuel);
            float smoke=f.y*(1.-smoothstep(.07,.39,fuel))*smoothstep(.16,.78,turbulence);
            float sootWeight=1.45*smoke;
            float fireWeight=2.35*hot*(.32+1.2*turbulence*turbulence);
            float weight=fireWeight+sootWeight;
            alpha=(1.-exp(-weight))*(1.-smoothstep(.82,1.,age/life))*smoothstep(0.,.028,age);
            float luminous=clamp(fuel*.89+.53*(turbulence-.47),0.,1.);
            vec3 emission=mix(vec3(.55,.042,.006),vec3(2.5,.52,.045),smoothstep(.075,.55,luminous));
            emission=mix(emission,vec3(4.15,2.45,.84),smoothstep(.61,.96,luminous));
            color=mix(vec3(.071,.065,.069),emission,fireWeight/max(weight,.0001));
          }else{
            float fade=sin(samplePoint.y*3.14159)*(1.-smoothstep(.74,1.,age/life));
            if(surface>2.5){
              float rag=.14*sin(coord.y*18.+seed)+.10*cos(coord.y*29.);
              float edge=1.-smoothstep(.77,1.,abs(coord.x)+rag);
              float carbon=smoothstep(.29,.65,samplePoint.y+.17*coord.y+.06*sin(coord.x*10.));
              float liveEdge=1.-smoothstep(.02,.15,abs(samplePoint.y+.17*coord.y-.50));
              color=mix(vec3(1.48,.76,.24),vec3(.063,.047,.036),carbon)+liveEdge*vec3(.78,.16,.025);
              alpha=fade*edge*.95;
            }else{
            alpha=fade*(1.-coord.x*coord.x)*sin(coord.y*3.14159);
            color=mix(vec3(.81,.11,.022),vec3(2.9,1.02,.22),1.-samplePoint.y);
            }
          }
          if(alpha<.008)discard;
          flameColor=vec4(color,alpha);
          #ifdef TONE_MAPPING
            flameColor.rgb=toneMapping(flameColor.rgb);
          #endif
          flameColor=linearToOutputTexel(flameColor);
        }`,
    });
    super(geometry,material);
    this.name="eruption";
    this.onBeforeRender=(_renderer,_scene,camera)=>{
      const eye=material.uniforms.eyeLocal.value;
      camera.getWorldPosition(eye);
      this.worldToLocal(eye);
      this.material.uniformsNeedUpdate=true;
    };
  }
  burn(age: number, duration: number) {
    this.visible = age > -.8 && age < duration;
    // Only the stone quad needs rasterizing while the ground is heating.
    this.geometry.setDrawRange(0,age < 0 ? 6 : Infinity);
    this.material.uniforms.age.value=age;
    this.material.uniforms.life.value=duration;
  }
}
