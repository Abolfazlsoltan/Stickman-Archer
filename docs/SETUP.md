# Stickman Archer - Full Setup Guide

## 1. Import into Unity

- Create new 2D URP or Built-in project (recommended URP for glow effects).
- Copy the `Assets` folder contents into your project.
- Create folders: Sprites/Base, Sprites/Variants, Sprites/Weapons, Prefabs, Materials.

## 2. Character Hierarchy (Recommended)

```
StickmanArcher (Root)
├── Body (SpriteRenderer + Rigidbody2D + CapsuleCollider2D)
├── Scarf (SpriteRenderer - child for layering)
├── Quiver (SpriteRenderer)
├── Bow (SpriteRenderer + optional Animator for string)
├── Eyes (SpriteRenderer or Particle for glow)
├── FirePoint (empty Transform at hand)
└── Bones (for Ragdoll)
    ├── Head
    ├── Torso
    ├── UpperArm_L / UpperArm_R
    ├── LowerArm_L / LowerArm_R
    ├── UpperLeg_L / UpperLeg_R
    └── LowerLeg_L / LowerLeg_R
```

## 3. Animator Controller

Create Animator Controller with these states:

- Idle (default)
- Walk (blend tree on Speed)
- Run
- Draw
- Shoot
- Hit
- Fall
- Death

Transitions:
- Any → Hit (trigger Hit)
- Any → Death (bool IsDead)
- Idle/Walk/Run → Draw (bool IsDrawing)
- Draw → Shoot (exit time or trigger)

## 4. Materials for Glow

For the glowing eyes and bow energy:
- Use Sprite Lit or Unlit with Emission.
- Cyan emission color matching the concept (#00E5FF).

## 5. Prefab

1. Assemble hierarchy.
2. Add all scripts.
3. Configure references in Inspector.
4. Drag to Prefabs folder → Make Prefab.

## 6. Arrow Prefab

Simple sprite + Rigidbody2D + CapsuleCollider2D (isTrigger) + ArrowProjectile script.

Different materials/colors for variants or change at runtime.

## Next Steps

- Import the original concept image as reference.
- Generate or hand-paint sprite sheets matching the animation poses.
- For 3D version: Model in Blender following the views, export FBX with humanoid/generic rig.

Enjoy building!
