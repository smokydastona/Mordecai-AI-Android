from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WhisperSettings:
    binary: str = "whisper"
    model: str = "base"
    language: str | None = None
    device: str | None = None


class WhisperTranscriber:
    def __init__(self, settings: WhisperSettings | None = None) -> None:
        self.settings = settings or WhisperSettings()

    def build_command(self, audio_path: Path, output_dir: Path) -> list[str]:
        command = [
            self.settings.binary,
            str(audio_path),
            "--model",
            self.settings.model,
            "--output_format",
            "txt",
            "--output_dir",
            str(output_dir),
        ]
        if self.settings.language:
            command.extend(["--language", self.settings.language])
        if self.settings.device:
            command.extend(["--device", self.settings.device])
        return command

    def transcribe(self, audio_path: Path) -> str:
        if shutil.which(self.settings.binary) is None:
            raise RuntimeError(f"'{self.settings.binary}' is not installed or not on PATH")
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = subprocess.run(
                self.build_command(audio_path, output_dir),
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "whisper transcription failed")
            transcript_path = output_dir / f"{audio_path.stem}.txt"
            if not transcript_path.exists():
                raise RuntimeError("Whisper did not produce a transcript file")
            return transcript_path.read_text(encoding="utf-8").strip()