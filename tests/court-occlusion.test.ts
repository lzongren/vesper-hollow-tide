import assert from "node:assert/strict";
import test from "node:test";
import * as T from "three";
import { SSAOPass } from "three/addons/postprocessing/SSAOPass.js";
import { classifyCourtSurface, CourtOcclusion } from "../src/court-occlusion";

test("mist stays visible in the beauty and reflection cameras without filling the depth buffer", () => {
  const mist = new T.Mesh(new T.PlaneGeometry(), new T.MeshBasicMaterial({ transparent: true, depthWrite: false }));
  const foliage = new T.Mesh(new T.PlaneGeometry(), new T.MeshStandardMaterial({ alphaTest: .4 }));
  const camera = new T.PerspectiveCamera();
  classifyCourtSurface(mist);
  classifyCourtSurface(foliage);
  assert.equal(camera.layers.test(mist.layers), false);
  assert.equal(camera.layers.test(foliage.layers), true);
  camera.layers.enable(1);
  assert.equal(camera.layers.test(mist.layers), true);
  assert.equal(camera.layers.test(foliage.layers), true);
});

test("depth-pass failure still restores all camera layers and the shadow update policy", t => {
  const camera = new T.PerspectiveCamera();
  camera.layers.enable(1);
  camera.layers.enable(5);
  const mask = camera.layers.mask;
  const renderer = { shadowMap: { autoUpdate: true } } as T.WebGLRenderer;
  t.mock.method(SSAOPass.prototype, "render", () => {
    assert.equal(camera.layers.isEnabled(1), false);
    assert.equal(camera.layers.isEnabled(5), true);
    assert.equal(renderer.shadowMap.autoUpdate, false);
    throw Error("render interrupted");
  });
  const target = new T.WebGLRenderTarget(1, 1);
  const occlusion = new CourtOcclusion(new T.Scene(), camera, 1, 1);
  assert.throws(() => occlusion.render(renderer, target, target, .016, false), /render interrupted/);
  assert.equal(camera.layers.mask, mask);
  assert.equal(renderer.shadowMap.autoUpdate, true);
});
