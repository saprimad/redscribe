"""Strict primary benchmark configuration checks, without GPU dependencies."""
def verify_configuration(device, precision):
    if str(device).split(":")[0] != "cuda" or str(precision) not in ("float16", "torch.float16"):
        raise RuntimeError(f"Benchmark configuration mismatch or unverified: device={device}, precision={precision}; expected CUDA FP16")
    return "cuda", "float16"

def verify_parameters(parameters):
    seen = False
    for p in parameters:
        if p.is_floating_point():
            verify_configuration(p.device, p.dtype)
            seen = True
        elif str(p.device).split(":")[0] != "cuda":
            raise RuntimeError("Benchmark configuration mismatch: non-CUDA parameter")
    if not seen:
        raise RuntimeError("Benchmark configuration unverified: no floating-point parameters")
    return "cuda", "float16"
