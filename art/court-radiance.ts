import * as T from "three";
import { World } from "../src/scene";

const names = ["belfry","garden","shrine"];
const request = new URLSearchParams(location.search);
const court = names.indexOf(request.get("court") ?? "belfry");
if (court < 0) throw new Error("Choose belfry, garden or shrine");
const world = new World(document.querySelector("canvas")!);
await world.ready;
await world.prepareCourt(court,true);
world.setArena(court);
world.scene.environmentIntensity = .64;
for(const node of [world.player.root,world.boss.root,world.lock,world.bladeTrail,world.rain]) node.visible=false;

// Refresh the wet paving's reflected image before measuring the stationary
// court. Capture without characters, game overlays or camera-space grading.
world.camera.position.set(0,2.15,-.4);
world.camera.lookAt(0,1,-12);
world.rainCourt.capture(world.renderer,world.scene,world.camera,1,"high");
const cube = new T.WebGLCubeRenderTarget(256,{type:T.HalfFloatType,generateMipmaps:false});
const eye = new T.CubeCamera(.08,200,cube);
eye.position.copy(world.camera.position);
eye.updateMatrixWorld(true);
eye.update(world.renderer,world.scene);

const width=512,height=256;
const panorama=new T.WebGLRenderTarget(width,height,{type:T.FloatType,depthBuffer:false});
const stage=new T.Scene();
const quad=new T.Mesh(new T.PlaneGeometry(2,2),new T.ShaderMaterial({
  uniforms:{radiance:{value:cube.texture}},
  vertexShader:`varying vec2 st;void main(){st=uv;gl_Position=vec4(position.xy,0.,1.);}`,
  fragmentShader:`uniform samplerCube radiance;varying vec2 st;
    void main(){float az=(st.x-.5)*6.2831853, el=(st.y-.5)*3.14159265;
    vec3 ray=vec3(cos(az)*cos(el),sin(el),sin(az)*cos(el));
    gl_FragColor=vec4(textureCube(radiance,ray).rgb,1.);}`,
}));
stage.add(quad);
world.renderer.setRenderTarget(panorama);
world.renderer.render(stage,new T.Camera());
const pixels=new Float32Array(width*height*4);
world.renderer.readRenderTargetPixels(panorama,0,0,width,height,pixels);
world.renderer.setRenderTarget(null);

// Radiance RGBE scanlines, top row first. Use literal packets of at most
// 128 values, including rows whose first pixel happens to resemble an RLE tag.
const header=new TextEncoder().encode(`#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y ${height} +X ${width}\n`);
const packed=new Uint8Array(header.length+height*(4+4*(width+width/128)));
packed.set(header);
let cursor=header.length;
const channels=new Uint8Array(4*width);
for(let y=height-1;y>=0;y--){
  for(let x=0;x<width;x++){
    const k=4*(y*width+x), peak=Math.max(pixels[k],pixels[k+1],pixels[k+2]);
    const power=peak>1e-24 ? Math.floor(Math.log2(peak))+1 : -128;
    const scale=power===-128 ? 0 : 2**(8-power);
    for(let c=0;c<3;c++)channels[c*width+x]=Math.min(255,Math.max(0,pixels[k+c]*scale));
    channels[3*width+x]=power+128;
  }
  packed.set([2,2,width>>8,width&255],cursor);cursor+=4;
  for(let i=0;i<channels.length;i+=128){
    packed[cursor++]=128;
    packed.set(channels.subarray(i,i+128),cursor);cursor+=128;
  }
}
const link=document.createElement("a");
link.href=URL.createObjectURL(new Blob([packed],{type:"application/octet-stream"}));
link.download=names[court]+"-court.hdr";link.textContent="Save "+link.download;
document.querySelector("#status")!.replaceChildren(link);
cube.dispose();panorama.dispose();quad.geometry.dispose();quad.material.dispose();
