using UnityEngine;

/// <summary>
/// Helper for clean animation state management and event callbacks.
/// Attach alongside Animator.
/// </summary>
public class ArcherAnimationController : MonoBehaviour
{
    private Animator anim;

    public System.Action OnShootFrame;
    public System.Action OnDrawComplete;
    public System.Action OnDeathComplete;

    void Awake()
    {
        anim = GetComponent<Animator>();
    }

    // Called from Animation Events
    public void AnimEvent_Shoot()
    {
        OnShootFrame?.Invoke();
    }

    public void AnimEvent_DrawComplete()
    {
        OnDrawComplete?.Invoke();
    }

    public void AnimEvent_DeathEnd()
    {
        OnDeathComplete?.Invoke();
    }

    public void CrossFade(string stateName, float transition = 0.1f)
    {
        anim.CrossFade(stateName, transition);
    }
}
