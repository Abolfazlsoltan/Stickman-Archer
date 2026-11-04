# Stickman Archer

**Simple Body • Powerful Soul**

> "Some archers don't just shoot arrows... They shoot destiny."

A complete, production-ready Stickman Archer character pack designed for 2D/2.5D games (Unity, Godot, etc.). Includes concept art, multi-view references, color variants, animation examples, weapon system, ragdoll readiness, and full Unity integration scripts.

![Concept Art](docs/concept.png)

## Features

- **Stylized Stickman Design**: Clean black body with glowing cyan eyes, flowing blue scarf/cape, detailed quiver, belt with crystal, and ornate glowing bow.
- **Multiple Views**: Front, Side, Back, 3/4 views for perfect reference.
- **Color Variants**: Blue (Default), Red, Gold, Green, Purple — easy to recolor or generate more.
- **Animation Set** (examples included):
  - Idle
  - Walk
  - Run
  - Draw (bow)
  - Shoot
  - Hit
  - Fall
  - Death
- **Ragdoll Ready**: Full joint hierarchy, Rigidbody, Colliders, Hinge joints, custom weights for realistic physics.
- **Weapon & Arrows**:
  - Normal
  - Explosive (red)
  - Poison (green)
  - Ice (purple/cyan)
- **Game Ready Formats**:
  - Unity (scripts + prefab structure)
  - PNG Sprites / Textures
  - FBX (3D Model ready structure)
  - PSD Source (layered)
- **Modular Details**: Head & Scarf, Quiver & Arrows, Belt & Armor, Bow Detail

## Repository Structure

```
Stickman-Archer/
├── README.md
├── docs/
│   ├── concept.png          # Full character sheet
│   ├── views/               # Individual view images
│   └── animations/          # Animation frame examples
├── Assets/
│   ├── Scripts/
│   │   ├── StickmanArcherController.cs
│   │   ├── ArcherAnimationController.cs
│   │   ├── RagdollController.cs
│   │   ├── ArrowProjectile.cs
│   │   └── ColorVariantSwitcher.cs
│   ├── Prefabs/
│   │   └── StickmanArcher.prefab (instructions)
│   ├── Sprites/
│   │   ├── Base/
│   │   ├── Variants/
│   │   └── Weapons/
│   └── Materials/
├── UnityProject/            # Optional full Unity project notes
└── LICENSE
```

## Quick Start (Unity)

1. Clone this repo into your Unity project's `Assets` folder or import as package.
2. Create an empty GameObject → Add `StickmanArcherController`.
3. Assign Animator with the provided states (Idle → Walk → Run → Draw → Shoot → Hit → Fall → Death).
4. For ragdoll: Use the provided `RagdollController` and set up HingeJoint2D / CharacterJoint on the bone hierarchy.
5. Shoot: Call `ShootArrow(ArrowType.Normal)` or variants.

### Example Usage

```csharp
var archer = GetComponent<StickmanArcherController>();
archer.PlayAnimation(ArcherAnim.Draw);
archer.Shoot(ArrowType.Explosive);
```

## Color Variants

| Variant | Primary Color | Accent |
|---------|---------------|--------|
| Blue (Default) | #00B4D8 | Cyan glow |
| Red | #E63946 | Crimson |
| Gold | #FFD60A | Warm gold |
| Green | #2EC4B6 / #06D6A0 | Emerald |
| Purple | #9B5DE5 | Violet |

Use `ColorVariantSwitcher` script or recolor materials/sprites.

## Animation States

Recommended Animator parameters:
- `Speed` (float)
- `IsDrawing` (bool)
- `IsShooting` (trigger)
- `IsHit` (trigger)
- `IsDead` (bool)

## Ragdoll Setup Notes

- Root: Rigidbody + CapsuleCollider
- Head, Torso, UpperArm L/R, LowerArm L/R, UpperLeg L/R, LowerLeg L/R
- Use HingeJoint2D for 2D or CharacterJoint for 3D
- Custom mass distribution for realistic fall
- Enable on death / heavy hit

## Weapons System

Arrows support different behaviors:
- **Normal**: Standard damage + velocity
- **Explosive**: Area damage on impact
- **Poison**: DoT effect
- **Ice**: Slow / freeze

Extend `ArrowProjectile` for custom logic.

## Credits & License

Original concept and design based on the provided character sheet.

MIT License — free for personal and commercial use in games.

Built with ❤️ for the Stickman community and Small Warriors-style projects.

---

**Simple Body, Powerful Soul.**
