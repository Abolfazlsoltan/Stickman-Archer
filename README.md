# Stickman Archer

Stylized stickman archer as a **real glTF 2.0 model** with a joint hierarchy and authored animation clips.

This is not the cinematic painting from the character sheet, and it is not a smooth-skinned high-poly sculpt. It is a segmented 3D stickman (rigid volumes parented to bones) that imports into Blender, Unity (glTFast), Godot, and Three.js and **plays**.

## What is actually in this repository

| File | What it is |
|---|---|
| [models/StickmanArcher.glb](models/StickmanArcher.glb) | Rigged model, materials, 5 color variants, 12 animation clips |
| [tools/generate_stickman.py](tools/generate_stickman.py) | Generator that builds that GLB. Re-runnable, no manual DCC step |
| `Assets/Scripts/*.cs` | Earlier Unity 2D controller sketches. They are **not** wired to the GLB |

Not included, because they were not produced: FBX, PSD, PNG sprite sheets, hand-painted textures, smooth skin weights, a Unity Humanoid avatar.

## Model facts

- Units: meters. Up: +Y. Facing: +Z.
- About 1.42 m to the top of the head. Feet rest near the ground.
- 34 nodes. Volumes parented to joints (head, torso, arms, legs, scarf chain, quiver, bow, crystal).
- Materials are solid PBR colors. Eyes, crystal, arrow tips, and scarf accents use emissive factors. There is no texture image.
- Color variants use `KHR_materials_variants`: **Blue** (default), **Red**, **Gold**, **Green**, **Purple**. They recolor the scarf and the emissive parts. Blender's glTF importer and Unity glTFast both read this extension. Engines that ignore it still show the Blue default.

## Animations

All clips are keyframed rotations (plus hips translation). Loop flags are not a core glTF field; set looping in the engine from this table.

| Clip | Duration | Loop in engine |
|---|---|---|
| Idle | 2.40 s | yes |
| Walk | 1.00 s | yes |
| Run | 0.60 s | yes |
| Jump | 0.90 s | no |
| Landing | 0.45 s | no |
| Turn | 0.55 s | no |
| Celebrate | 1.00 s | yes |
| Draw | 0.45 s | no |
| Shoot | 0.40 s | no |
| Hit | 0.45 s | no |
| Fall | 0.60 s | no |
| Death | 1.40 s | no |

Walk and Run are in place. Jump, Fall, and Death move the hips. Verified by loading the file with Three.js `GLTFLoader` and sampling `AnimationMixer`: the walk cycle changes the thigh rotation, and jump raises the hips.

## Use it

### Blender

File → Import → glTF 2.0 → `models/StickmanArcher.glb`.  
The dope sheet lists the clips. Material variants show up if your Blender build exposes glTF variants (4.x does, under the mesh material slots / variant UI).

### Unity (glTFast)

1. Add the [glTFast](https://docs.unity3d.com/Packages/com.unity.cloud.gltfast@6.0/manual/index.html) package.
2. Drop `StickmanArcher.glb` into `Assets`.
3. The importer creates a prefab, materials, and `AnimationClip` assets named Idle, Walk, Run, and the rest.
4. Put an Animator on the prefab root. Add the clips as states. Mark Idle, Walk, Run, and Celebrate as Loop Time.
5. To swap color: select the variant in the glTFast importer (Materials Variants) or duplicate the imported materials and assign `Scarf_*` / `Glow_*`.

The old scripts under `Assets/Scripts` expect a 2D `Rigidbody2D` and sprite renderers. Do not drop them on this model.

### Godot 4

Import the GLB. The scene contains the skeleton hierarchy and an `AnimationPlayer` with the twelve clips.

### Three.js

```js
const gltf = await loader.loadAsync("./models/StickmanArcher.glb");
const mixer = new THREE.AnimationMixer(gltf.scene);
mixer.clipAction(gltf.animations.find((c) => c.name === "Walk")).play();
```

## Rebuild

```bash
python3 tools/generate_stickman.py
```

Writes `models/StickmanArcher.glb` next to the script when you copy it, or edit `OUT` in the script. Needs only the Python standard library.

## License

MIT. See [LICENSE](LICENSE).
