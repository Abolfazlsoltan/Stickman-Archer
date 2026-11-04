# Scripts Overview

## StickmanArcherController.cs
Main brain of the character.
- Movement (walk/run)
- Input handling (example keyboard/mouse)
- Draw & Shoot pipeline with coroutine
- Damage / Death integration with ragdoll
- Public API: `PlayAnimation()`, `ShootArrow()`, `TakeDamage()`, `Die()`

## ArrowProjectile.cs
Handles all 4 arrow types with different impact behaviors.
Extend the switch cases for custom status effects (DoT, slow, etc.).

## RagdollController.cs
Toggles between animated and physics-driven modes.
Populate the lists with every bone Rigidbody2D and Collider2D in the Inspector.

## ColorVariantSwitcher.cs
One-click recolor system matching the official 5 variants from the character sheet.

## ArcherAnimationController.cs
Animation Event bridge. Use `AnimEvent_Shoot` etc. in your Animation clips.
