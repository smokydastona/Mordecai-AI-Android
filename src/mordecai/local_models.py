from __future__ import annotations

import shlex
import shutil
from pathlib import Path

from mordecai.config import Settings
from mordecai.models import LocalModelCatalogSnapshot, LocalModelProfileSnapshot
from mordecai_core.models.local_models import LocalModelRegistry, ModelProfile


class LocalModelService:
    def __init__(self, settings: Settings, registry: LocalModelRegistry | None = None) -> None:
        self.settings = settings
        self.registry = registry or LocalModelRegistry()

    def list_profiles(self) -> list[LocalModelProfileSnapshot]:
        return [self._snapshot(profile) for profile in self.registry.load()]

    def catalog_snapshot(self) -> LocalModelCatalogSnapshot:
        profiles = self.list_profiles()
        return LocalModelCatalogSnapshot(
            models_dir=self.settings.models_dir.as_posix(),
            available_profiles=sum(1 for profile in profiles if profile.binary_available and profile.enabled),
            configured_profiles=len(profiles),
            profiles=profiles,
        )

    def capability_manifest(self) -> list[dict[str, object]]:
        return [profile.model_dump(mode="json") for profile in self.list_profiles()]

    def _snapshot(self, profile: ModelProfile) -> LocalModelProfileSnapshot:
        binary = self._command_binary(profile.command)
        model_path = self._resolve_model_path(profile.model_path)
        return LocalModelProfileSnapshot(
            name=profile.name,
            provider=profile.provider,
            modality=profile.modality,
            command=profile.command,
            context_window=profile.context_window,
            enabled=profile.enabled,
            prompt_format=profile.prompt_format,
            model_path=model_path.as_posix() if model_path else None,
            binary_available=shutil.which(binary) is not None if binary else False,
            model_available=model_path.exists() if model_path else False,
        )

    def _resolve_model_path(self, value: str | None) -> Path | None:
        if not value:
            return None
        raw = Path(value)
        return raw if raw.is_absolute() else (self.settings.models_dir / raw)

    @staticmethod
    def _command_binary(command: str) -> str | None:
        parts = shlex.split(command)
        return parts[0] if parts else None