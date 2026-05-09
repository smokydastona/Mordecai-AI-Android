from __future__ import annotations

import os
import time
from dataclasses import dataclass

try:
    import resource
except ImportError:
    resource = None

try:
    import psutil
except ImportError:
    psutil = None

from mordecai.config import Settings


@dataclass
class ResourceSnapshot:
    cpu_percent: float
    memory_mb: float
    healthy: bool
    reason: str


class _WatchdogBackend:
    def cpu_percent(self) -> float:
        raise NotImplementedError

    def memory_mb(self) -> float:
        raise NotImplementedError


class _PsutilBackend(_WatchdogBackend):
    def __init__(self) -> None:
        self.process = psutil.Process(os.getpid())

    def cpu_percent(self) -> float:
        return self.process.cpu_percent(interval=0.0)

    def memory_mb(self) -> float:
        return self.process.memory_info().rss / 1024 / 1024


class _FallbackBackend(_WatchdogBackend):
    def __init__(self) -> None:
        self._last_cpu_time = self._process_cpu_time()
        self._last_wall_time = time.monotonic()

    def cpu_percent(self) -> float:
        current_cpu_time = self._process_cpu_time()
        current_wall_time = time.monotonic()
        cpu_delta = max(0.0, current_cpu_time - self._last_cpu_time)
        wall_delta = max(0.0, current_wall_time - self._last_wall_time)
        self._last_cpu_time = current_cpu_time
        self._last_wall_time = current_wall_time
        if wall_delta == 0.0:
            return 0.0
        return min(100.0, max(0.0, (cpu_delta / wall_delta) * 100.0))

    def memory_mb(self) -> float:
        if resource is not None:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            rss = float(usage.ru_maxrss)
            if os.name == "posix" and os.uname().sysname == "Darwin":
                return rss / 1024 / 1024
            return rss / 1024
        return 0.0

    @staticmethod
    def _process_cpu_time() -> float:
        process_times = os.times()
        return process_times.user + process_times.system


class Watchdog:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backend = _PsutilBackend() if psutil is not None else _FallbackBackend()

    def snapshot(self) -> ResourceSnapshot:
        cpu_percent = self.backend.cpu_percent()
        memory_mb = self.backend.memory_mb()
        healthy = cpu_percent <= self.settings.max_cpu_percent and memory_mb <= self.settings.max_memory_mb
        if healthy:
            reason = "within limits"
        else:
            reason = "resource threshold exceeded"
        return ResourceSnapshot(cpu_percent=cpu_percent, memory_mb=memory_mb, healthy=healthy, reason=reason)