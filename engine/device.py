try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

def detect_rocm_device() -> str:
    """Detects AMD ROCm HIP GPU runtime or falls back to CPU.

    FIX: the original fallback string was
    "AMD ROCm-Ready Deterministic Graph Engine" even when no GPU was
    present at all. That misleads a judge/demo viewer into thinking
    ROCm ran. The fallback now says CPU plainly.
    """
    if TORCH_AVAILABLE and torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        hip = getattr(torch.version, "hip", None)
        return f"AMD ROCm GPU ({name} | HIP {hip})" if hip else f"GPU ({name})"
    return "CPU (deterministic graph engine - ROCm GPU not detected)"
