using UnityEngine;

/// <summary>
/// Instantly switch between the 5 official color variants of Stickman Archer.
/// </summary>
public class ColorVariantSwitcher : MonoBehaviour
{
    public enum Variant { Blue, Red, Gold, Green, Purple }

    [System.Serializable]
    public class VariantColors
    {
        public Color body = Color.black;
        public Color scarf;
        public Color glow;
        public Color accent;
    }

    [Header("Renderers")]
    public SpriteRenderer bodyRenderer;
    public SpriteRenderer scarfRenderer;
    public SpriteRenderer quiverRenderer;
    public SpriteRenderer bowRenderer;
    public SpriteRenderer eyesRenderer; // if separate

    [Header("Variant Definitions")]
    public VariantColors blue = new VariantColors
    {
        scarf = new Color(0.1f, 0.55f, 0.95f),
        glow = new Color(0.2f, 0.85f, 1f),
        accent = new Color(0.3f, 0.7f, 1f)
    };
    public VariantColors red = new VariantColors
    {
        scarf = new Color(0.9f, 0.2f, 0.2f),
        glow = new Color(1f, 0.3f, 0.2f),
        accent = new Color(1f, 0.4f, 0.2f)
    };
    public VariantColors gold = new VariantColors
    {
        scarf = new Color(1f, 0.75f, 0.1f),
        glow = new Color(1f, 0.85f, 0.3f),
        accent = new Color(1f, 0.7f, 0.1f)
    };
    public VariantColors green = new VariantColors
    {
        scarf = new Color(0.15f, 0.85f, 0.45f),
        glow = new Color(0.2f, 1f, 0.5f),
        accent = new Color(0.1f, 0.9f, 0.4f)
    };
    public VariantColors purple = new VariantColors
    {
        scarf = new Color(0.65f, 0.3f, 0.95f),
        glow = new Color(0.8f, 0.4f, 1f),
        accent = new Color(0.7f, 0.35f, 1f)
    };

    public void SetVariant(Variant v)
    {
        VariantColors c = v switch
        {
            Variant.Red => red,
            Variant.Gold => gold,
            Variant.Green => green,
            Variant.Purple => purple,
            _ => blue
        };

        if (scarfRenderer) scarfRenderer.color = c.scarf;
        if (quiverRenderer) quiverRenderer.color = c.accent;
        if (bowRenderer) bowRenderer.color = c.accent;
        // Eyes / glow usually handled by emission or separate material
        if (eyesRenderer) eyesRenderer.color = c.glow;
    }

    // Editor / runtime buttons
    [ContextMenu("Set Blue")] void SetBlue() => SetVariant(Variant.Blue);
    [ContextMenu("Set Red")] void SetRed() => SetVariant(Variant.Red);
    [ContextMenu("Set Gold")] void SetGold() => SetVariant(Variant.Gold);
    [ContextMenu("Set Green")] void SetGreen() => SetVariant(Variant.Green);
    [ContextMenu("Set Purple")] void SetPurple() => SetVariant(Variant.Purple);
}
