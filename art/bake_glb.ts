import { writeFile } from "node:fs/promises";
import * as T from "three";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
// The exporter's binary path uses this one FileReader operation on Node.
class BinaryReader {
  result?: ArrayBuffer;
  onloadend?: () => void;
  async readAsArrayBuffer(blob: Blob) {
    this.result = await blob.arrayBuffer();
    this.onloadend?.();
  }
}
Object.defineProperty(globalThis, "FileReader", {
  value: BinaryReader,
  configurable: true,
});

export async function bake(
  prop: T.Group,
  name: string,
  animations: T.AnimationClip[] = [],
) {
  prop.name = name;
  const output = await new GLTFExporter().parseAsync(prop, {
    binary: true,
    animations,
  });
  if (!(output instanceof ArrayBuffer))
    throw Error("Expected a binary glTF asset");
  await writeFile(
    new URL(`../native/Art/${name}.glb`, import.meta.url),
    new Uint8Array(output),
  );
}
