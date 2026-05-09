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
    catalog_slug: str | None = None
    runtime_fit: str | None = None
    integration_tier: str | None = None
    install_asset_ids: list[str] | None = None


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
                name="llama.cpp-qwen2.5-3b",
                provider="llama.cpp",
                modality="chat",
                command="llama-cli -m Qwen2.5-3B-Instruct-Q4_K_M.gguf -c 8192",
                context_window=8192,
                model_path="Qwen2.5-3B-Instruct-Q4_K_M.gguf",
                prompt_format="chatml",
            ),
            ModelProfile(
                name="llamafile-gemma-3-1b",
                provider="llamafile",
                modality="chat",
                command="gemma-3-1b-it-Q4_K_M.llamafile --ctx-size 8192",
                context_window=8192,
                model_path="gemma-3-1b-it-Q4_K_M.llamafile",
                prompt_format="chatml",
            ),
            ModelProfile(
                name="whisper-cli",
                provider="whisper",
                modality="stt",
                command="whisper audio.wav --model base --output_format txt",
                context_window=0,
                catalog_slug="whisper",
                runtime_fit="phone",
                integration_tier="managed",
            ),
            ModelProfile(
                name="piper-tts",
                provider="piper",
                modality="tts",
                command="piper --model en_US-lessac-medium.onnx --output_file speech.wav",
                context_window=0,
                model_path="en_US-lessac-medium.onnx",
                catalog_slug="piper",
                runtime_fit="phone",
                integration_tier="managed",
                install_asset_ids=["piper-en-us-lessac-medium-onnx", "piper-en-us-lessac-medium-config"],
            ),
            ModelProfile(
                name="whisper.cpp-base-en",
                provider="whisper.cpp",
                modality="stt",
                command="whisper-cli -m ggml-base.en.bin -f audio.wav",
                context_window=0,
                model_path="ggml-base.en.bin",
                catalog_slug="whisper-cpp",
                runtime_fit="phone",
                integration_tier="managed",
                install_asset_ids=["whispercpp-ggml-base-en"],
            ),
            ModelProfile(
                name="whisper.cpp-base-en-vad",
                provider="whisper.cpp",
                modality="stt",
                command="whisper-cli --vad --vad-model ggml-silero-v6.2.0.bin -m ggml-base.en.bin -f audio.wav",
                context_window=0,
                model_path="ggml-base.en.bin",
                catalog_slug="whisper-cpp",
                runtime_fit="phone",
                integration_tier="managed",
                install_asset_ids=["whispercpp-ggml-base-en", "whispercpp-silero-vad-v6"],
            ),
            ModelProfile(
                name="sherpa-onnx-whisper-tiny-en",
                provider="sherpa-onnx",
                modality="stt",
                command="sherpa-onnx-offline --whisper-encoder tiny.en-encoder.int8.onnx --whisper-decoder tiny.en-decoder.int8.onnx --tokens tiny.en-tokens.txt audio.wav",
                context_window=0,
                model_path="sherpa-onnx-whisper-tiny.en/mordecai-sherpa-manifest.json",
                catalog_slug="sherpa-onnx",
                runtime_fit="phone",
                integration_tier="managed",
                install_asset_ids=["sherpa-onnx-whisper-tiny-en-archive", "sherpa-onnx-silero-vad"],
            ),
        ]