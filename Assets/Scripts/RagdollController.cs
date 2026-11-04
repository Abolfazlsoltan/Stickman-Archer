using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// Enables / disables ragdoll physics for the Stickman Archer.
/// Attach to the root. Assign all Rigidbody2D / HingeJoint2D children.
/// </summary>
public class RagdollController : MonoBehaviour
{
    [Header("Bones / Rigidbodies")]
    public List<Rigidbody2D> boneBodies = new List<Rigidbody2D>();
    public List<Collider2D> boneColliders = new List<Collider2D>();

    [Header("Main Character Components")]
    public Rigidbody2D mainBody;
    public Collider2D mainCollider;
    public Animator animator;
    public StickmanArcherController controller;

    [Header("Settings")]
    public bool startAsRagdoll = false;

    private bool isRagdoll;

    void Start()
    {
        if (mainBody == null) mainBody = GetComponent<Rigidbody2D>();
        if (mainCollider == null) mainCollider = GetComponent<Collider2D>();
        if (animator == null) animator = GetComponent<Animator>();

        SetRagdoll(startAsRagdoll);
    }

    public void EnableRagdoll()
    {
        SetRagdoll(true);
    }

    public void DisableRagdoll()
    {
        SetRagdoll(false);
    }

    void SetRagdoll(bool enable)
    {
        isRagdoll = enable;

        // Disable animator & main controller physics
        if (animator) animator.enabled = !enable;
        if (controller) controller.enabled = !enable;

        if (mainBody)
        {
            mainBody.simulated = !enable;
            mainBody.bodyType = enable ? RigidbodyType2D.Kinematic : RigidbodyType2D.Dynamic;
        }
        if (mainCollider) mainCollider.enabled = !enable;

        // Enable bone physics
        foreach (var rb in boneBodies)
        {
            if (rb == null) continue;
            rb.simulated = enable;
            rb.bodyType = enable ? RigidbodyType2D.Dynamic : RigidbodyType2D.Kinematic;
            if (enable)
            {
                // Optional: transfer velocity from main body
                // rb.linearVelocity = mainBody.linearVelocity;
            }
        }

        foreach (var col in boneColliders)
        {
            if (col) col.enabled = enable;
        }
    }

    // Call this from animation event or death
    public void OnDeath()
    {
        EnableRagdoll();
    }
}
