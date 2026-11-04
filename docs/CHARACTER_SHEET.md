# Character Sheet Reference

## Core Identity
- **Name**: Stickman Archer
- **Tagline**: Simple Body, Powerful Soul
- **Quote**: "Some archers don't just shoot arrows... They shoot destiny."

## Visual Design
- Body: Pure black stickman silhouette
- Eyes: Bright cyan/blue glowing slits
- Scarf / Cape: Flowing blue fabric with dynamic folds
- Quiver: Back-mounted with blue arrows + glowing tips
- Belt: Dark with central cyan crystal
- Bow: Ornate dark wood/metal with cyan energy string and arrow

## Official Color Variants
1. **Blue (Default)** – Primary cyan/blue energy
2. **Red** – Aggressive crimson
3. **Gold** – Prestigious warm gold
4. **Green** – Nature / poison theme
5. **Purple** – Arcane / shadow theme

## Animation List (Minimum Recommended)
| State     | Description                          | Loop |
|-----------|--------------------------------------|------|
| Idle      | Standing, slight scarf movement      | Yes  |
| Walk      | Moderate pace                        | Yes  |
| Run       | Fast forward lean                    | Yes  |
| Draw      | Pulling string, aiming               | No   |
| Shoot     | Release + recoil                     | No   |
| Hit       | Impact reaction                      | No   |
| Fall      | Airborne / knocked back              | No   |
| Death     | Collapse into ragdoll pose           | No   |

## Weapon System
- **Normal Arrow**: Clean blue tip
- **Explosive**: Red/orange glowing tip + AOE
- **Poison**: Green toxic tip + DoT
- **Ice**: Cyan/purple crystal tip + slow

## Technical Specs (Recommended)
- Sprite resolution: 512×512 or 1024×1024 per frame for high quality
- Pivot: Bottom center for 2D side-view
- Bones: 10–12 for good ragdoll (head, torso, 2 arms ×2, 2 legs ×2)
- Colliders: Capsule for torso/head, boxes or capsules for limbs

## Integration Tips for Small Warriors / Stickman Games
This character is designed to fit side-view stickman army battles.
Keep the body thin and readable at small sizes. Glow effects should be subtle so they don't overpower the silhouette.
