from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from datetime import UTC, datetime
from uuid import uuid4
import re
from typing import Any

from mordecai.config import Settings


@dataclass(frozen=True)
class VoiceProfile:
    wake_words: list[str]
    startup_phrase: str
    nicknames: dict[str, str]


class VoiceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def engines(self) -> dict[str, Any]:
        piper_model = self._default_piper_model()
        piper_config = Path(f"{piper_model}.json") if piper_model else None
        whisper_binary = shutil.which("whisper")
        piper_binary = shutil.which("piper")
        return {
            "piper": {
                "available": piper_binary is not None,
                "binary": piper_binary,
                "model": piper_model.as_posix() if piper_model else None,
                "model_exists": piper_model.exists() if piper_model else False,
                "config": piper_config.as_posix() if piper_config else None,
                "config_exists": piper_config.exists() if piper_config else False,
            },
            "whisper": {
                "available": whisper_binary is not None,
                "binary": whisper_binary,
            },
        }

    def synthesize(self, text: str, output_filename: str | None = None) -> dict[str, Any]:
        self._validate_text(text)
        piper_binary = shutil.which("piper")
        if piper_binary is None:
            raise RuntimeError("piper binary is not available on PATH")

        model_path = self._default_piper_model()
        if model_path is None or not model_path.exists():
            raise RuntimeError("Piper voice model is not installed; install the phone-starter bundle first")

        config_path = Path(f"{model_path}.json")
        if not config_path.exists():
            raise RuntimeError("Piper voice config is missing; install the phone-starter bundle first")

        voice_dir = self.settings.data_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._safe_output_name(output_filename)
        output_path = voice_dir / safe_name
        command = [
            piper_binary,
            "--model",
            model_path.as_posix(),
            "--config",
            config_path.as_posix(),
            "--output_file",
            output_path.as_posix(),
        ]
        result = subprocess.run(command, input=text, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "piper synthesis failed")
        if not output_path.exists():
            raise RuntimeError("piper did not produce an output file")

        return {
            "engine": "piper",
            "output_path": output_path.as_posix(),
            "bytes": output_path.stat().st_size,
            "created_at": datetime.now(UTC).isoformat(),
        }

    def transcribe(self, audio_path: str, model: str = "base") -> dict[str, Any]:
        whisper_binary = shutil.which("whisper")
        if whisper_binary is None:
            raise RuntimeError("whisper binary is not available on PATH")

        source = Path(audio_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Audio file not found: {source.as_posix()}")

        voice_dir = self.settings.data_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)
        command = [
            whisper_binary,
            source.as_posix(),
            "--model",
            model,
            "--output_format",
            "txt",
            "--output_dir",
            voice_dir.as_posix(),
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "whisper transcription failed")

        transcript_path = voice_dir / f"{source.stem}.txt"
        if not transcript_path.exists():
            raise RuntimeError("whisper did not produce a transcript file")

        text = transcript_path.read_text(encoding="utf-8").strip()
        return {
            "engine": "whisper",
            "model": model,
            "audio_path": source.as_posix(),
            "transcript_path": transcript_path.as_posix(),
            "text": text,
        }

    def _default_piper_model(self) -> Path | None:
        models_dir = self.settings.models_dir
        if models_dir is None:
            return None
        return models_dir / "en_US-lessac-medium.onnx"

    @staticmethod
    def _safe_output_name(output_filename: str | None) -> str:
        if not output_filename:
            return f"tts-{uuid4().hex[:12]}.wav"
        cleaned = output_filename.strip()
        if not cleaned.lower().endswith(".wav"):
            cleaned += ".wav"
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", cleaned):
            raise ValueError("output_filename can only contain letters, numbers, dot, underscore, and dash")
        return cleaned

    @staticmethod
    def _validate_text(text: str) -> None:
        stripped = text.strip()
        if not stripped:
            raise ValueError("Text cannot be empty")
        if len(stripped) > 2000:
            raise ValueError("Text must be 2000 characters or fewer")


def build_voice_profile(settings: Settings) -> VoiceProfile:
    return VoiceProfile(
        wake_words=settings.wake_words,
        startup_phrase="I am listening.",
        nicknames={
            "Mordecai": "formal",
            "Mori": "soft",
            "Cai": "efficient",
            "Morde": "focused",
            "Mort": "diagnostic",
            "Decai": "analytical",
        },
    )