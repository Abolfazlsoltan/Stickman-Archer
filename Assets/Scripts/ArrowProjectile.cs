using UnityEngine;

/// <summary>
/// Projectile logic for different arrow types: Normal, Explosive, Poison, Ice.
/// </summary>
[RequireComponent(typeof(Rigidbody2D))]
public class ArrowProjectile : MonoBehaviour
{
    public enum ArrowType { Normal, Explosive, Poison, Ice }

    [Header("Settings")]
    public float lifetime = 5f;
    public float damage = 10f;
    public GameObject hitEffect;
    public GameObject explosionEffect;
    public GameObject poisonCloud;
    public GameObject iceEffect;

    private ArrowType type;
    private Rigidbody2D rb;
    private bool hasHit;

    void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
        Destroy(gameObject, lifetime);
    }

    public void Initialize(ArrowType arrowType, Vector2 direction, float force)
    {
        type = arrowType;
        rb.linearVelocity = direction.normalized * force;

        // Optional: rotate to face direction
        float angle = Mathf.Atan2(direction.y, direction.x) * Mathf.Rad2Deg;
        transform.rotation = Quaternion.AngleAxis(angle, Vector3.forward);

        ApplyVisuals();
    }

    void ApplyVisuals()
    {
        // Change trail / sprite color based on type
        var sr = GetComponentInChildren<SpriteRenderer>();
        if (sr == null) return;

        switch (type)
        {
            case ArrowType.Explosive:
                sr.color = new Color(1f, 0.3f, 0.1f);
                break;
            case ArrowType.Poison:
                sr.color = new Color(0.2f, 0.9f, 0.3f);
                break;
            case ArrowType.Ice:
                sr.color = new Color(0.4f, 0.8f, 1f);
                break;
            default:
                sr.color = Color.white;
                break;
        }
    }

    void OnTriggerEnter2D(Collider2D other)
    {
        if (hasHit) return;
        if (other.CompareTag("Player") || other.isTrigger) return; // ignore self / friendly

        hasHit = true;
        rb.linearVelocity = Vector2.zero;
        rb.bodyType = RigidbodyType2D.Kinematic;

        // Apply effect
        switch (type)
        {
            case ArrowType.Explosive:
                Explode();
                break;
            case ArrowType.Poison:
                ApplyPoison(other);
                break;
            case ArrowType.Ice:
                ApplyIce(other);
                break;
            default:
                ApplyDamage(other, damage);
                break;
        }

        if (hitEffect) Instantiate(hitEffect, transform.position, Quaternion.identity);
        Destroy(gameObject, 0.1f);
    }

    void Explode()
    {
        if (explosionEffect) Instantiate(explosionEffect, transform.position, Quaternion.identity);

        Collider2D[] hits = Physics2D.OverlapCircleAll(transform.position, 2.5f);
        foreach (var h in hits)
        {
            ApplyDamage(h, damage * 1.5f);
            // Add force for knockback
            var r = h.attachedRigidbody;
            if (r) r.AddForce((h.transform.position - transform.position).normalized * 8f, ForceMode2D.Impulse);
        }
    }

    void ApplyPoison(Collider2D target)
    {
        ApplyDamage(target, damage * 0.6f);
        // TODO: Add PoisonStatus component or call health.ApplyDoT
        if (poisonCloud) Instantiate(poisonCloud, transform.position, Quaternion.identity);
    }

    void ApplyIce(Collider2D target)
    {
        ApplyDamage(target, damage * 0.8f);
        // TODO: Slow / freeze the target
        if (iceEffect) Instantiate(iceEffect, transform.position, Quaternion.identity);
    }

    void ApplyDamage(Collider2D target, float dmg)
    {
        // Simple interface - extend with IDamageable
        var health = target.GetComponent<MonoBehaviour>(); // replace with real health
        // health?.TakeDamage(dmg);
        Debug.Log($"Arrow ({type}) hit {target.name} for {dmg} damage");
    }
}
