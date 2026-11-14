import * as T from "three";
function isMesh(o: T.Object3D): o is T.Mesh {
  return (o as T.Mesh).isMesh === true;
}
import { GLTFLoader, type GLTF } from "three/addons/loaders/GLTFLoader.js";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { clone } from "three/addons/utils/SkeletonUtils.js";

export class ArtLibrary {
  models = new Map<string, GLTF>();
  textures = new Map<string, T.Texture>();
  environment?: T.DataTexture;
  private seals = new Map<string, T.MeshStandardMaterial>();

  async courtSeal(name: string) {
    const existing = this.seals.get(name);
    if (existing) return existing;
    const loader = new T.TextureLoader();
    const base = `${import.meta.env.BASE_URL}textures/seal-${name}`;
    const [color, normal, orm] = await Promise.all(
      ["color", "normal", "orm"].map((channel) =>
        loader.loadAsync(`${base}-${channel}.jpg`),
      ),
    );
    for (const map of [color, normal, orm]) map.anisotropy = 8;
    color.colorSpace = T.SRGBColorSpace;
    const material = new T.MeshStandardMaterial({
      name: `${name} engraved stone and bronze`,
      map: color,
      normalMap: normal,
      roughness: 1,
      metalness: 1,
      roughnessMap: orm,
      metalnessMap: orm,
      aoMap: orm,
    });
    this.seals.set(name, material);
    return material;
  }

  async loadLandmark(name: string) {
    if (this.models.has(name)) return;
    const model = await new GLTFLoader().loadAsync(
      `${import.meta.env.BASE_URL}models/${name}.glb`,
    );
    this.models.set(name, model);
  }
  async load() {
    const gltf = new GLTFLoader(),
      images = new T.TextureLoader();
    const base = import.meta.env.BASE_URL;
    await Promise.all([
      ...[
        "pilgrim",
        "wraith",
        "sorcerer",
        "sword",
        "pine",
        "dead-tree",
        "tide-bell",
      ].map(async (name) => {
        this.models.set(
          name,
          await gltf.loadAsync(`${base}models/${name}.glb`),
        );
      }),
      ...["stone", "wall", "rock", "wood", "metal"].flatMap((name) =>
        ["color", "normal", "rough"].map(async (channel) => {
          const texture = await images.loadAsync(
            `${base}textures/${name}-${channel}.jpg`,
          );
          texture.wrapS = texture.wrapT = T.RepeatWrapping;
          texture.anisotropy = 8;
          if (channel === "color") texture.colorSpace = T.SRGBColorSpace;
          this.textures.set(`${name}-${channel}`, texture);
        }),
      ),
      ...["color", "normal"].map(async (channel) => {
        const map = await images.loadAsync(
          `${base}textures/pilgrim-brocade-${channel}.jpg`,
        );
        if (channel === "color") map.colorSpace = T.SRGBColorSpace;
        map.anisotropy = 8;
        this.textures.set(`pilgrim-brocade-${channel}`, map);
      }),
      ...[
        "karst-valley",
        "tide-icon",
        "lacquer-bay",
        "heron-silk",
        "cinder-mask",
        "dragon-mantle",
        "rain-stones",
        "heron-quill",
        "warden-mask",
      ].map(async (name) => {
        const map = await images.loadAsync(
          `${base}art/${name}.${name === "heron-quill" || name === "warden-mask" ? "png" : "jpg"}`,
        );
        map.colorSpace = T.SRGBColorSpace;
        map.anisotropy = 8;
        this.textures.set(name, map);
      }),
      new HDRLoader().loadAsync(`${base}textures/moonlight.hdr`).then((t) => {
        t.mapping = T.EquirectangularReflectionMapping;
        this.environment = t;
      }),
    ]);
  }
  model(name: string, height: number) {
    const source = this.models.get(name);
    if (!source) throw new Error(`Missing model: ${name}`);
    const model = clone(source.scene);
    model.updateMatrixWorld(true);
    const bounds = new T.Box3().setFromObject(model),
      size = bounds.getSize(new T.Vector3()),
      center = bounds.getCenter(new T.Vector3());
    if (name === "sword") {
      model.rotation.z = -Math.PI / 2;
      model.updateMatrixWorld(true);
      bounds.setFromObject(model);
      bounds.getSize(size);
      bounds.getCenter(center);
    }
    const scale = height / size.y;
    model.scale.multiplyScalar(scale);
    model.position.set(
      -center.x * scale,
      -bounds.min.y * scale,
      -center.z * scale,
    );
    const group = new T.Group();
    group.add(model);
    group.traverse((o) => {
      if (isMesh(o)) {
        o.castShadow = o.receiveShadow = true;
        o.userData.sharedGeometry = true;
        const multiple = Array.isArray(o.material);
        const materials = multiple
          ? (o.material as T.Material[])
          : [o.material as T.Material];
        const copies = materials.map((m) => {
          const c = m.clone() as T.MeshStandardMaterial;
          c.envMapIntensity = 1.3;
          if (c.map) c.map.anisotropy = 8;
          return c;
        });
        o.material = multiple ? copies : copies[0];
      }
    });
    return group;
  }
  material(name: string, repeatX = 1, repeatY = repeatX, color = 0xffffff) {
    const copy = (kind: string) => {
      const t = this.textures.get(`${name}-${kind}`)!.clone();
      t.repeat.set(repeatX, repeatY);
      t.needsUpdate = true;
      return t;
    };
    return new T.MeshStandardMaterial({
      color,
      map: copy("color"),
      normalMap: copy("normal"),
      roughnessMap: copy("rough"),
      roughness: 1,
      metalness: name === "metal" ? 0.75 : 0.05,
      normalScale: new T.Vector2(0.65, 0.65),
    });
  }
}
