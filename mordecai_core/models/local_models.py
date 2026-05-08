from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from mordecai.config import ensure_state_dirs, get_settings


@dataclass(slots=True)
class ModelProfile:
    name: str
    provider: str
    modality: str
    command: str
    context_window: int
    enabled: bool = True
    model_path: str | None = None
    prompt_format: str | None = None


class LocalModelRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        settings = get_settings()
        ensure_state_dirs(settings)
        self.registry_path = registry_path or settings.state_dir / "local_models.json"

    def load(self) -> list[ModelProfile]:
        if not self.registry_path.exists():
            profiles = self.default_profiles()
            self.save(profiles)
            return profiles
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return [ModelProfile(**item) for item in payload]

    def save(self, profiles: list[ModelProfile]) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(profile) for profile in profiles]
        self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get(self, name: str) -> ModelProfile:
        for profile in self.load():
            if profile.name == name:
                return profile
        raise KeyError(f"Unknown model profile '{name}'")

    @staticmethod
    def default_profiles() -> list[ModelProfile]:
        return [
            ModelProfile(
                name="mordecai-cloud",
                provider="openai-compatible",
                modality="chat",
                command="python -m mordecai_core.agent --interactive",
                context_window=8192,
                prompt_format="chat-completions",
            ),
            ModelProfile(
                name="ollama-local",
                provider="ollama",
                modality="chat",
                command="ollama run llama3.1",
                context_window=8192,
            ),
            ModelProfile(
                name="whisper-cli",
                provider="whisper",
                modality="stt",
                command="whisper audio.wav --model base --output_format txt",
                context_window=0,
            ),
            ModelProfile(
                name="piper-tts",
                provider="piper",
                modality="tts",
                command="piper --model voice.onnx --output_file speech.wav",
                context_window=0,
            ),
        ]