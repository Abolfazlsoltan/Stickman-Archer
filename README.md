# Stickman Archer

**Simple Body • Powerful Soul**

> "Some archers don't just shoot arrows... They shoot destiny."

A complete, production-ready **Stickman Archer** character pack designed for 2D/2.5D games (Unity, Godot, etc.).  
Includes multi-view references, 5 official color variants, full animation state design, weapon system (4 arrow types), ragdoll readiness, and ready-to-use Unity C# scripts.

---

## Features

- **Stylized Stickman Design**  
  Clean black body • Glowing cyan eyes • Flowing blue scarf/cape • Detailed quiver • Crystal belt • Ornate energy bow

- **Multiple Views**  
  Front • Side • Back • 3/4

- **Color Variants**  
  Blue (Default) • Red • Gold • Green • Purple

- **Animation Set**  
  Idle • Walk • Run • Draw • Shoot • Hit • Fall • Death

- **Ragdoll Ready**  
  Full joint hierarchy, Rigidbody, Colliders, Hinge joints, custom weights

- **Weapon & Arrows**  
  Normal • Explosive • Poison • Ice

- **Game Ready**  
  Unity scripts + structure • PNG / Sprite ready • FBX-ready hierarchy notes • PSD-friendly modular design

---

## Repository Structure

```
Stickman-Archer/
├── README.md
├── LICENSE
├── .gitignore
├── docs/
│   ├── SETUP.md
│   ├── CHARACTER_SHEET.md
│   └── (add concept.png + view images here)
└── Assets/
    └── Scripts/
        ├── StickmanArcherController.cs
        ├── ArrowProjectile.cs
        ├── RagdollController.cs
        ├── ColorVariantSwitcher.cs
        ├── ArcherAnimationController.cs
        └── README_SCRIPTS.md
```

---

## Quick Start (Unity)

1. Clone or download this repository.
2. Copy the `Assets/Scripts` folder into your Unity project.
3. Create your character GameObject hierarchy (see `docs/SETUP.md`).
4. Add the scripts and wire the references in the Inspector.
5. Create an Animator Controller with the recommended states and parameters.
6. (Optional) Drop the original character sheet image into `docs/concept.png` for reference.

### Example Code

```csharp
var archer = GetComponent<StickmanArcherController>();

// Play states
archer.PlayAnimation(StickmanArcherController.ArcherAnim.Draw);

// Shoot different arrows
archer.ShootArrow(StickmanArcherController.ArrowType.Explosive);
archer.ShootArrow(StickmanArcherController.ArrowType.Ice);
```

---

## Color Variants

| Variant | Primary | Glow / Accent |
|---------|---------|---------------|
| **Blue** (Default) | `#00B4D8` | Cyan |
| **Red** | `#E63946` | Crimson |
| **Gold** | `#FFD60A` | Warm Gold |
| **Green** | `#06D6A0` | Emerald |
| **Purple** | `#9B5DE5` | Violet |

Use the `ColorVariantSwitcher` component for instant switching.

---

## Recommended Animator Parameters

- `Speed` (float)
- `IsDrawing` (bool)
- `Shoot` (trigger)
- `Hit` (trigger)
- `IsDead` (bool)

---

## Adding Your Own Art

1. Place the full character sheet as `docs/concept.png`.
2. Export individual views into `docs/views/`.
3. Create sprite sheets for each animation and put them in `Assets/Sprites/`.
4. For 3D: Model following the orthographic views → export FBX with the bone hierarchy described in SETUP.md.

---

## License

MIT License — free for personal and commercial games.

---

**Simple Body, Powerful Soul.**

Built for stickman-style projects and army battle games.
