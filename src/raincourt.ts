import * as T from "three";
import { GroundRite, riteSurface } from "./rites";
import { Reflector } from "three/addons/objects/Reflector.js";

/** A single reflected view is projected into the wet parts of the stone's PBR
 * shader. Dry high spots keep the original material and its contact shadows. */
const surface = /* glsl */ `
uniform sampler2D courtMirror;
uniform mat4 courtProject;
uniform float courtTime, courtWet, courtSeed;
uniform vec4 courtSteps[6];
uniform vec4 courtImpact;
uniform float courtImpactFan;
uniform vec4 courtSoles[4];
uniform vec4 courtToes[4];
varying vec3 courtPoint;
float poolHash(vec2 p) {
  vec3 p3=fract(vec3(p.xyx)*.1031);
  p3+=dot(p3,p3.yzx+33.33);
  return fract((p3.x+p3.y)*p3.z);
}
float poolNoise(vec2 p){
  vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
  return mix(mix(poolHash(i),poolHash(i+vec2(1,0)),f.x),
    mix(poolHash(i+vec2(0,1)),poolHash(i+1.),f.x),f.y);
}
vec2 rainRing(vec2 p, float t) {
  vec2 cell=floor(p);
  float seed=poolHash(cell);
  vec2 center=.28+.44*vec2(seed,poolHash(cell+14.7));
  vec2 delta=fract(p)-center;
  float radius=length(delta), age=fract(t*.73+seed*8.);
  float wave=radius-age*.37;
  return delta/max(.008,radius)*cos(86.*wave)*exp(-85.*abs(wave))*(1.-age);
}
`;

export class RainCourt {
  readonly rite = new GroundRite();
  readonly floor = new T.Group();
  private mirror = new Reflector(new T.PlaneGeometry(1, 1), {
    textureWidth: 640,
    textureHeight: 360,
    multisample: 0,
    clipBias: 0.0003,
  });
  private mirrorInverse = new T.Matrix4();
  private project = new T.Matrix4();
  private step = Array.from({ length: 6 }, () => new T.Vector4(0, 0, -10, 0));
  private soles = Array.from({ length: 4 }, () => new T.Vector4(0, 0, 0.1, 0));
  private toes = Array.from({ length: 4 }, () => new T.Vector4());
  private toe = new T.Vector3();
  private ankle = new T.Vector3();
  private strike = { value: new T.Vector4(0, 0, -10, 0) };
  private strikeFan = { value: 0 };
  private clock = { value: 0 };
  private wet = { value: 0 };
  private seed = { value: 0 };
  private lastCapture = -10;
  private cursor = 0;
  constructor() {
    this.mirror.camera.layers.enable(1);
    this.mirror.rotation.x = -Math.PI / 2;
    this.mirror.position.y = -0.002;
    this.mirror.updateMatrixWorld();
    this.mirrorInverse.copy(this.mirror.matrixWorld).invert();
    this.floor.name = "Wet court paving";
  }
  setArena(index: number) {
    this.seed.value = [3.4, 31.7, 85.2][index];
    this.wet.value = [0.51, 0.49, 0.37][index];
    this.lastCapture = -10;
    this.strike.value.z = -10;
    this.step.forEach((s) => (s.z = -10));
  }
  gardenWater() {
    const material = new T.MeshStandardMaterial({
      color: 0x243b32, roughness: 0.19, metalness: 0.14, side: T.DoubleSide,
    });
    material.customProgramCacheKey = () => "garden-pool-water";
    material.onBeforeCompile = shader => {
      Object.assign(shader.uniforms, {
        courtMirror: { value: this.mirror.getRenderTarget().texture },
        courtProject: { value: this.project }, courtTime: this.clock,
      });
      shader.vertexShader = "varying vec3 courtPoint;\n" + shader.vertexShader.replace(
        "#include <project_vertex>",
        "#include <project_vertex>\n courtPoint=(modelMatrix*vec4(transformed,1.)).xyz;",
      );
      shader.fragmentShader = surface + shader.fragmentShader.replace(
        "#include <opaque_fragment>", `
          vec2 p=courtPoint.xz;
          vec2 wind=vec2(sin(p.x*3.7+p.y*1.5+courtTime*1.8),cos(p.y*5.1+p.x*.9+courtTime*1.2));
          vec2 ripple=rainRing(p*1.17,courtTime)+rainRing(p*1.63+9.7,courtTime*.83);
          vec4 projected=courtProject*vec4(courtPoint,1.);
          vec2 uv=projected.xy/max(projected.w,.001);
          float edge=smoothstep(.0,.035,min(min(uv.x,1.-uv.x),min(uv.y,1.-uv.y)));
          vec2 ones=clamp(uv+wind*.0012+ripple*.002,.002,.998);
          vec3 sky=texture2D(courtMirror,ones).rgb;
          float grazing=1.-clamp(normalize(cameraPosition-courtPoint).y,.0,1.);
          outgoingLight=mix(outgoingLight,sky,edge*(.28+.58*grazing*grazing));
          #include <opaque_fragment>`,
      );
    };
    return material;
  }

  finishStone(material: T.MeshStandardMaterial, inlay = false) {
    material.customProgramCacheKey = () =>
      inlay ? "wet-jointed-medallion" : "wet-paving";
    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, {
        courtMirror: { value: this.mirror.getRenderTarget().texture },
        courtProject: { value: this.project },
        courtTime: this.clock,
        courtWet: this.wet,
        courtSeed: this.seed,
        courtSteps: { value: this.step },
        courtImpact: this.strike,
        courtImpactFan: this.strikeFan,
        courtSoles: { value: this.soles },
        courtToes: { value: this.toes },
        ritePose: this.rite.pose,
        riteExtent: this.rite.extent,
        riteCharge: this.rite.charge,
      });
      shader.vertexShader =
        "varying vec3 courtPoint;\n" +
        shader.vertexShader.replace(
          "#include <project_vertex>",
          "#include <project_vertex>\n courtPoint=(modelMatrix*vec4(transformed,1.)).xyz;",
        );
      shader.fragmentShader =
        surface + riteSurface +
        shader.fragmentShader
          .replace(
            "#include <roughnessmap_fragment>",
            `#include <roughnessmap_fragment>
          vec2 p=courtPoint.xz, basin=p*vec2(.31,.44)+courtSeed;
          float height=.54*poolNoise(basin)+.28*poolNoise(basin*2.13+3.)+.12*poolNoise(basin*5.8)+.06*poolNoise(basin*14.3);
          float grain=poolNoise(p*8.5+vec2(1.7,4.1));
          height+=.052*(grain-.5);
          ${inlay ? `// The extra drainage and top elevation are registered to this slab.
          height += .29*(texelRoughness.r-.5) + 3.0*(courtPoint.y+.018);` : ""}
          float pool=smoothstep(height-.024,height+.024,courtWet-.042);
          float damp=smoothstep(height-.15,height+.11,courtWet);
          diffuseColor.rgb *= mix(1.,.75,damp);
          float baseRoughness=roughnessFactor;
          float dampRoughness=mix(baseRoughness,max(.39,baseRoughness*.81),damp);
          roughnessFactor=mix(dampRoughness,.18+.13*grain,pool);`,
          )
          .replace(
            "#include <opaque_fragment>",
            `
          if(pool>.002) {
            vec2 ripple=rainRing(p*2.1,courtTime)+.65*rainRing(p*2.76+7.3,courtTime*1.12);
            for(int i=0;i<6;i++){
              vec2 d=p-courtSteps[i].xy;
              float age=courtTime-courtSteps[i].z;
              if(age>=0. && age<1.3) {
                float r=length(d), f=r-age*1.6;
                ripple+=d/max(.01,r)*cos(f*37.)*exp(-abs(f)*11.)*(1.-age/1.3)*courtSteps[i].w;
              }
            }
            float age=courtTime-courtImpact.z;
            vec2 delta=p-courtImpact.xy;
            float distanceToStrike=length(delta);
            if(age>=0. && age<.72 && distanceToStrike<4.1) {
              vec2 dir=delta/max(.01,distanceToStrike);
              float facing=dot(dir,vec2(sin(courtImpact.w),cos(courtImpact.w)));
              float fan=mix(1.,smoothstep(.26,.65,facing),courtImpactFan);
              float crest=distanceToStrike-age*6.;
              ripple+=dir*fan*2.8*cos(crest*32.)*exp(-abs(crest)*6.)*(1.-age/.72);
            }
            vec4 projected=courtProject*vec4(courtPoint,1.);
            vec2 uv=projected.xy/projected.w;
            float grazing=1.-clamp(normalize(cameraPosition-courtPoint).y,0.,1.);
            vec2 jitter=(ripple*.0022+vec2(sin(p.x*21.+p.y*11.),cos(p.y*13.-p.x*9.))*.00062)*(.4+grazing);
            vec2 at=clamp(uv+jitter,.002,.998);
            vec3 mirror=texture2D(courtMirror,at).rgb;
            float margin=smoothstep(0.,.035,min(min(uv.x,1.-uv.x),min(uv.y,1.-uv.y)));
            float fresnel=.045+.51*pow(grazing,3.2);
            outgoingLight=mix(outgoingLight,mirror,pool*fresnel*margin);
          }
          float occlusion=0.;
          for(int i=0;i<4;i++){
            vec2 heel=courtSoles[i].xy, axis=courtToes[i].xy-heel;
            float along=clamp(dot(p-heel,axis)/max(dot(axis,axis),.00001),0.,1.);
            float width=mix(courtSoles[i].z,courtToes[i].z,along);
            float contact=mix(courtSoles[i].w,courtToes[i].w,along);
            vec2 offset=(p-heel-along*axis)/max(width,.005);
            float r2=dot(offset,offset);
            occlusion=max(occlusion,contact*(.79*exp(-r2*1.62)+.21*exp(-r2*.35)));
          }
          outgoingLight += waterWriting(p,pool,diffuseColor.rgb);
          outgoingLight*=1.-occlusion;
          #include <opaque_fragment>`,
          );
    };
  }

  sole(index: number, bone: T.Bone | undefined, toeBone: T.Bone | undefined, height: number) {
    const heel = this.soles[index], tip = this.toes[index];
    if (!bone || !toeBone) {
      heel.w = tip.w = 0;
      return;
    }
    bone.getWorldPosition(this.ankle);
    toeBone.getWorldPosition(this.toe);
    const dx = this.toe.x - this.ankle.x, dz = this.toe.z - this.ankle.z;
    const heelLift = Math.max(0, this.ankle.y - height * 0.064);
    const toeLift = Math.max(0, this.toe.y - height * 0.025);
    heel.set(this.ankle.x - dx * 0.20, this.ankle.z - dz * 0.20,
      height * 0.059 + heelLift * 0.28, 0.65 * Math.exp(-heelLift * 15 / height));
    tip.set(this.toe.x + dx * 0.14, this.toe.z + dz * 0.14,
      height * 0.055 + toeLift * 0.28, 0.68 * Math.exp(-toeLift * 16 / height));
  }

  impact(x: number, z: number, facing: number, sector: boolean) {
    this.strike.value.set(x, z, this.clock.value, facing);
    this.strikeFan.value = sector ? 1 : 0;
  }

  contact(x: number, z: number, strength: number) {
    this.step[this.cursor].set(x, z, this.clock.value, strength);
    this.cursor = (this.cursor + 1) % this.step.length;
  }
  capture(
    renderer: T.WebGLRenderer,
    scene: T.Scene,
    camera: T.PerspectiveCamera,
    time: number,
    quality: string,
  ) {
    this.clock.value = time;
    if (time - this.lastCapture < 1 / (quality === "low" ? 8 : 18)) return;
    this.lastCapture = time;
    camera.updateWorldMatrix(true, false);
    this.floor.visible = false;
    try {
      this.mirror.onBeforeRender(
        renderer,
        scene,
        camera,
        this.mirror.geometry,
        this.mirror.material as T.Material,
        null!,
      );
      const projected = (this.mirror.material as T.ShaderMaterial).uniforms
        .textureMatrix.value;
      this.project.copy(projected).multiply(this.mirrorInverse);
    } finally {
      this.floor.visible = true;
    }
  }
}
