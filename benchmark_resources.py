"""Optional GPU/CPU resource sampler for benchmark inference (no extra imports at module load).

Samples every 0.5s. nvidia-smi is optional; never fabricates GPU measurements.
"""
import csv
import shutil
import subprocess
import threading
import time


class ResourceMonitor:
    def __init__(self, interval=0.5):
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()
        self._thread = None
        self._start = None

    def __enter__(self):
        self._start = time.monotonic()
        self._thread = threading.Thread(target=self._collect, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _collect(self):
        cli = shutil.which("nvidia-smi")
        try:
            import psutil
        except ImportError:
            psutil = None
        while not self._stop.is_set():
            point = {"elapsed_s": round(time.monotonic() - self._start, 2),
                     "gpu_util_percent": None, "gpu_memory_used_mb": None,
                     "gpu_memory_total_mb": None, "gpu_temperature_c": None,
                     "cpu_percent": None, "ram_used_mb": None}
            if cli:
                try:
                    done = subprocess.run(
                        [cli, "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                         "--format=csv,noheader,nounits"],
                        capture_output=True, text=True, timeout=2, check=True)
                    # Capture GPU 0 consistently; log which GPU is sampled.
                    vals = [float(v.strip()) for v in done.stdout.splitlines()[0].split(",")]
                    if len(vals) == 4:
                        (point["gpu_util_percent"], point["gpu_memory_used_mb"],
                         point["gpu_memory_total_mb"], point["gpu_temperature_c"]) = vals
                except (OSError, subprocess.SubprocessError, ValueError, IndexError):
                    pass
            if psutil is not None:
                try:
                    point["cpu_percent"] = psutil.cpu_percent(interval=None)
                    point["ram_used_mb"] = round(psutil.virtual_memory().used / 1024**2, 2)
                except Exception:
                    pass
            self.samples.append(point)
            self._stop.wait(self.interval)

    def summary(self):
        numeric = ("gpu_util_percent", "gpu_memory_used_mb", "gpu_temperature_c",
                   "cpu_percent", "ram_used_mb")
        return {key + "_peak": max((x[key] for x in self.samples if x[key] is not None), default=None)
                for key in numeric} | {"sample_count": len(self.samples),
                                      "gpu_source": "nvidia-smi GPU index 0 (system-wide)",
                                      "ram_source": "system-wide (not process-specific)"}

    def save_csv(self, destination):
        if not self.samples:
            return
        with open(destination, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.samples[0].keys())
            writer.writeheader()
            writer.writerows(self.samples)
