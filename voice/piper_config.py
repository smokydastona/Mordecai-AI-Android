from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PiperVoiceConfig:
    model_path: Path
    binary: str = "piper"
    config_path: Path | None = None
    speaker_id: int | None = None
    length_scale: float | None = None


class PiperSpeaker:
    def __init__(self, config: PiperVoiceConfig) -> None:
        self.config = config

    def build_command(self, output_path: Path) -> list[str]:
        command = [self.config.binary, "--model", str(self.config.model_path), "--output_file", str(output_path)]
        if self.config.config_path is not None:
            command.extend(["--config", str(self.config.config_path)])
        if self.config.speaker_id is not None:
            command.extend(["--speaker", str(self.config.speaker_id)])
        if self.config.length_scale is not None:
            command.extend(["--length_scale", str(self.config.length_scale)])
        return command

    def synthesize(self, text: str, output_path: Path) -> Path:
        if shutil.which(self.config.binary) is None:
            raise RuntimeError(f"'{self.config.binary}' is not installed or not on PATH")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            self.build_command(output_path),
            input=text,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "piper synthesis failed")
        if not output_path.exists():
            raise RuntimeError("Piper did not produce an output file")
        return output_path