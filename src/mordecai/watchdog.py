from __future__ import annotations

import os
from dataclasses import dataclass

import psutil

from mordecai.config import Settings


@dataclass
class ResourceSnapshot:
    cpu_percent: float
    memory_mb: float
    healthy: bool
    reason: str


class Watchdog:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.process = psutil.Process(os.getpid())

    def snapshot(self) -> ResourceSnapshot:
        cpu_percent = self.process.cpu_percent(interval=0.0)
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        healthy = cpu_percent <= self.settings.max_cpu_percent and memory_mb <= self.settings.max_memory_mb
        if healthy:
            reason = "within limits"
        else:
            reason = "resource threshold exceeded"
        return ResourceSnapshot(cpu_percent=cpu_percent, memory_mb=memory_mb, healthy=healthy, reason=reason)