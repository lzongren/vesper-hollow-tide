import * as T from "three";
import { SSAOPass } from "three/addons/postprocessing/SSAOPass.js";

// Beauty and water reflections include airborne effects; the normal/depth pass
// must only see the first solid surface. Layer zero is the solid court.
const effectsLayer = 1;

export function markNonOccluding(mesh: T.Object3D) {
  mesh.layers.set(effectsLayer);
}

export function classifyCourtSurface(object: T.Object3D) {
  if (!(object instanceof T.Mesh)) return;
  const materials = Array.isArray(object.material) ? object.material : [object.material];
  if (materials.every(m => m.transparent && !m.depthWrite)) markNonOccluding(object);
}

export class CourtOcclusion extends SSAOPass {
  override render(
    renderer: T.WebGLRenderer,
    write: T.WebGLRenderTarget,
    read: T.WebGLRenderTarget,
    dt: number,
    maskActive: boolean,
  ) {
    const previousMask = this.camera.layers.mask;
    const autoShadows = renderer.shadowMap.autoUpdate;
    this.camera.layers.disable(effectsLayer);
    // The preceding beauty pass just rendered the current actor shadow maps.
    renderer.shadowMap.autoUpdate = false;
    try {
      super.render(renderer, write, read, dt, maskActive);
    } finally {
      this.camera.layers.mask = previousMask;
      renderer.shadowMap.autoUpdate = autoShadows;
    }
  }
}
