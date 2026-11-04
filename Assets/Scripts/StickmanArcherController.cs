using UnityEngine;
using System;

/// <summary>
/// Main controller for Stickman Archer character.
/// Handles movement, combat, state transitions, and integration with animation + ragdoll.
/// </summary>
[RequireComponent(typeof(Rigidbody2D))]
[RequireComponent(typeof(Animator))]
public class StickmanArcherController : MonoBehaviour
{
    public enum ArcherAnim
    {
        Idle,
        Walk,
        Run,
        Draw,
        Shoot,
        Hit,
        Fall,
        Death
    }

    public enum ArrowType
    {
        Normal,
        Explosive,
        Poison,
        Ice
    }

    [Header("Movement")]
    public float walkSpeed = 3.5f;
    public float runSpeed = 6.5f;
    public float jumpForce = 8f;

    [Header("Combat")]
    public Transform firePoint;
    public GameObject arrowPrefab;
    public float shootForce = 18f;
    public float drawTime = 0.45f;

    [Header("References")]
    public Animator animator;
    public RagdollController ragdoll;
    public SpriteRenderer bodyRenderer;
    public SpriteRenderer scarfRenderer;
    public SpriteRenderer quiverRenderer;

    // Runtime
    private Rigidbody2D rb;
    private bool isGrounded = true;
    private bool isDrawing;
    private bool isDead;
    private float currentSpeed;

    // Animator hashes
    private static readonly int SpeedHash = Animator.StringToHash("Speed");
    private static readonly int IsDrawingHash = Animator.StringToHash("IsDrawing");
    private static readonly int ShootTrigger = Animator.StringToHash("Shoot");
    private static readonly int HitTrigger = Animator.StringToHash("Hit");
    private static readonly int IsDeadHash = Animator.StringToHash("IsDead");

    void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
        if (animator == null) animator = GetComponent<Animator>();
    }

    void Update()
    {
        if (isDead) return;

        // Example input (replace with your input system)
        float h = Input.GetAxisRaw("Horizontal");
        bool run = Input.GetKey(KeyCode.LeftShift);

        currentSpeed = Mathf.Abs(h) * (run ? runSpeed : walkSpeed);
        animator.SetFloat(SpeedHash, currentSpeed);

        // Flip
        if (h != 0)
        {
            Vector3 scale = transform.localScale;
            scale.x = Mathf.Sign(h) * Mathf.Abs(scale.x);
            transform.localScale = scale;
        }

        // Movement
        rb.linearVelocity = new Vector2(h * (run ? runSpeed : walkSpeed), rb.linearVelocity.y);

        // Jump
        if (Input.GetButtonDown("Jump") && isGrounded)
        {
            rb.AddForce(Vector2.up * jumpForce, ForceMode2D.Impulse);
            isGrounded = false;
        }

        // Draw & Shoot
        if (Input.GetMouseButtonDown(0) && !isDrawing)
        {
            StartCoroutine(DrawAndShoot(ArrowType.Normal));
        }

        if (Input.GetKeyDown(KeyCode.Alpha1)) StartCoroutine(DrawAndShoot(ArrowType.Normal));
        if (Input.GetKeyDown(KeyCode.Alpha2)) StartCoroutine(DrawAndShoot(ArrowType.Explosive));
        if (Input.GetKeyDown(KeyCode.Alpha3)) StartCoroutine(DrawAndShoot(ArrowType.Poison));
        if (Input.GetKeyDown(KeyCode.Alpha4)) StartCoroutine(DrawAndShoot(ArrowType.Ice));
    }

    System.Collections.IEnumerator DrawAndShoot(ArrowType type)
    {
        isDrawing = true;
        animator.SetBool(IsDrawingHash, true);
        yield return new WaitForSeconds(drawTime);

        animator.SetBool(IsDrawingHash, false);
        animator.SetTrigger(ShootTrigger);

        ShootArrow(type);
        isDrawing = false;
    }

    public void ShootArrow(ArrowType type)
    {
        if (arrowPrefab == null || firePoint == null) return;

        GameObject arrow = Instantiate(arrowPrefab, firePoint.position, firePoint.rotation);
        var proj = arrow.GetComponent<ArrowProjectile>();
        if (proj != null)
        {
            proj.Initialize(type, transform.localScale.x > 0 ? Vector2.right : Vector2.left, shootForce);
        }
        else
        {
            Rigidbody2D arb = arrow.GetComponent<Rigidbody2D>();
            if (arb) arb.linearVelocity = (transform.localScale.x > 0 ? Vector2.right : Vector2.left) * shootForce;
        }
    }

    public void PlayAnimation(ArcherAnim anim)
    {
        switch (anim)
        {
            case ArcherAnim.Idle:
                animator.SetFloat(SpeedHash, 0f);
                break;
            case ArcherAnim.Walk:
                animator.SetFloat(SpeedHash, walkSpeed);
                break;
            case ArcherAnim.Run:
                animator.SetFloat(SpeedHash, runSpeed);
                break;
            case ArcherAnim.Draw:
                animator.SetBool(IsDrawingHash, true);
                break;
            case ArcherAnim.Shoot:
                animator.SetTrigger(ShootTrigger);
                break;
            case ArcherAnim.Hit:
                animator.SetTrigger(HitTrigger);
                break;
            case ArcherAnim.Death:
                Die();
                break;
        }
    }

    public void TakeDamage(float amount)
    {
        if (isDead) return;
        animator.SetTrigger(HitTrigger);
        // Add health system here
    }

    public void Die()
    {
        if (isDead) return;
        isDead = true;
        animator.SetBool(IsDeadHash, true);

        if (ragdoll != null)
        {
            ragdoll.EnableRagdoll();
        }
        else
        {
            // Fallback: disable collider / freeze
            GetComponent<Collider2D>().enabled = false;
            rb.linearVelocity = Vector2.zero;
            rb.bodyType = RigidbodyType2D.Kinematic;
        }
    }

    void OnCollisionEnter2D(Collision2D col)
    {
        if (col.gameObject.CompareTag("Ground"))
            isGrounded = true;
    }
}
