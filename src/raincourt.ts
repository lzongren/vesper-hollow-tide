import * as T from "three";
import { Reflector } from "three/addons/objects/Reflector.js";

/** A single reflected view is projected into the wet parts of the stone's PBR
 * shader. Dry high spots keep the original material and its contact shadows. */
const surface = /* glsl */ `
uniform sampler2D courtMirror;
uniform mat4 courtProject;
uniform float courtTime, courtWet, courtSeed;
uniform vec4 courtSteps[6];
uniform vec4 courtSoles[4];
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
  private ankle = new T.Vector3();
  private clock = { value: 0 };
  private wet = { value: 0 };
  private seed = { value: 0 };
  private lastCapture = -10;
  private cursor = 0;
  constructor() {
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
    this.step.forEach((s) => (s.z = -10));
  }
  finishStone(material: T.MeshStandardMaterial, inlay = false) {
    material.customProgramCacheKey = () =>
      inlay ? "wet-bronze-inlay" : "wet-paving";
    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, {
        courtMirror: { value: this.mirror.getRenderTarget().texture },
        courtProject: { value: this.project },
        courtTime: this.clock,
        courtWet: this.wet,
        courtSeed: this.seed,
        courtSteps: { value: this.step },
        courtSoles: { value: this.soles },
      });
      shader.vertexShader =
        "varying vec3 courtPoint;\n" +
        shader.vertexShader.replace(
          "#include <project_vertex>",
          "#include <project_vertex>\n courtPoint=(modelMatrix*vec4(transformed,1.)).xyz;",
        );
      shader.fragmentShader =
        surface +
        shader.fragmentShader
          .replace(
            "#include <roughnessmap_fragment>",
            `#include <roughnessmap_fragment>
          vec2 p=courtPoint.xz, basin=p*vec2(.31,.44)+courtSeed;
          float height=.54*poolNoise(basin)+.28*poolNoise(basin*2.13+3.)+.12*poolNoise(basin*5.8)+.06*poolNoise(basin*14.3);
          float pool=smoothstep(height-.028,height+.028,courtWet);
          float damp=smoothstep(height-.14,height+.06,courtWet);
          diffuseColor.rgb *= mix(1.,.55,damp);
          roughnessFactor=mix(roughnessFactor,.16,damp*.60+pool*.34);`,
          )
          .replace(
            "#include <metalnessmap_fragment>",
            `#include <metalnessmap_fragment>
          ${inlay ? "metalnessFactor=.08+.63*smoothstep(.008,.065,diffuseColor.r-diffuseColor.b);" : ""}`,
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
            vec4 projected=courtProject*vec4(courtPoint,1.);
            vec2 uv=projected.xy/projected.w;
            float grazing=1.-clamp(normalize(cameraPosition-courtPoint).y,0.,1.);
            vec2 jitter=(ripple*.0022+vec2(sin(p.x*21.+p.y*11.),cos(p.y*13.-p.x*9.))*.00062)*(.4+grazing);
            vec2 at=clamp(uv+jitter,.002,.998);
            vec3 mirror=texture2D(courtMirror,at).rgb;
            float margin=smoothstep(0.,.035,min(min(uv.x,1.-uv.x),min(uv.y,1.-uv.y)));
            float fresnel=.11+.61*pow(grazing,2.6);
            outgoingLight=mix(outgoingLight,mirror,pool*fresnel*margin);
          }
          float occlusion=0.;
          for(int i=0;i<4;i++){
            vec2 offset=(p-courtSoles[i].xy)/courtSoles[i].z;
            occlusion=max(occlusion,courtSoles[i].w*exp(-dot(offset,offset)*1.7));
          }
          outgoingLight*=1.-occlusion;
          #include <opaque_fragment>`,
          );
    };
  }

  sole(index: number, bone: T.Bone | null, height: number) {
    const footprint = this.soles[index];
    if (!bone) {
      footprint.w = 0;
      return;
    }
    bone.getWorldPosition(this.ankle);
    const lift = Math.max(0, this.ankle.y - height * 0.064);
    footprint.set(
      this.ankle.x,
      this.ankle.z,
      height * 0.107 + lift * 0.23,
      0.54 * Math.exp((-lift * 5) / height),
    );
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
