import * as T from "three";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { FullScreenQuad } from "three/addons/postprocessing/Pass.js";

export function courtSamples(color: Int32Array, depth: Int32Array) {
  // An HDR renderbuffer and its depth attachment must support the same count.
  return Math.max(0, ...Array.from(color).filter(n => n >= 2 && n <= 4 && depth.includes(n)));
}

/** Resolve geometric coverage in linear HDR, before occlusion, bloom and tone
 * mapping. Only the opaque/transparent beauty draw needs a multisampled target. */
export class CourtBeauty extends RenderPass {
  private readonly target: T.WebGLRenderTarget;
  private readonly copy: FullScreenQuad;
  constructor(scene: T.Scene, camera: T.Camera, samples: number) {
    super(scene, camera);
    this.target = new T.WebGLRenderTarget(1, 1, {
      type: T.HalfFloatType, samples, resolveDepthBuffer: false,
    });
    this.target.texture.name = "Court HDR multisample resolve";
    this.copy = new FullScreenQuad(new T.MeshBasicMaterial({
      map: this.target.texture, toneMapped: false, depthTest: false, depthWrite: false,
      blending: T.NoBlending,
    }));
  }

  override setSize(width: number, height: number) {
    this.target.setSize(Math.max(1, Math.floor(width)), Math.max(1, Math.floor(height)));
  }

  override render(renderer: T.WebGLRenderer, write: T.WebGLRenderTarget, read: T.WebGLRenderTarget, dt: number, mask: boolean) {
    if (this.renderToScreen) {
      super.render(renderer, write, read, dt, mask);
      return;
    }
    super.render(renderer, write, this.target, dt, mask);
    renderer.setRenderTarget(read);
    this.copy.render(renderer);
  }

  override dispose() {
    this.target.dispose();
    this.copy.material.dispose();
    this.copy.dispose();
  }
}
