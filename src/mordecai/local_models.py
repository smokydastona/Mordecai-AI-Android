from __future__ import annotations

import argparse
import asyncio
import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

from mordecai.config import Settings
from mordecai.models import LocalModelAssetSnapshot, LocalModelBundleSnapshot, LocalModelCatalogSnapshot, LocalModelInstallRequest, LocalModelInstallResult, LocalModelProfileSnapshot
from mordecai.policy import PolicyEngine
from mordecai.proxy import SafeHttpClient
from mordecai.store import StateStore
from mordecai_core.models.local_models import LocalModelRegistry, ModelProfile


@dataclass(frozen=True, slots=True)
class ManagedModelAsset:
    asset_id: str
    display_name: str
    profile_name: str | None
    modality: str
    filename: str
    source_url: str
    description: str
    sha256: str | None = None
    max_bytes: int | None = None
    executable: bool = False


@dataclass(frozen=True, slots=True)
class ManagedModelBundle:
    bundle_id: str
    display_name: str
    description: str
    asset_ids: tuple[str, ...]


class LocalModelService:
    def __init__(
        self,
        settings: Settings,
        registry: LocalModelRegistry | None = None,
        proxy: SafeHttpClient | None = None,
        store: StateStore | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry or LocalModelRegistry()
        self.store = store or StateStore(settings.state_dir, settings.max_log_entries)
        self.proxy = proxy or SafeHttpClient(settings, PolicyEngine(settings), self.store)

    def list_profiles(self) -> list[LocalModelProfileSnapshot]:
        return [self._snapshot(profile) for profile in self.registry.load()]

    def list_assets(self) -> list[LocalModelAssetSnapshot]:
        return [self._asset_snapshot(asset) for asset in self.default_assets()]

    def list_bundles(self) -> list[LocalModelBundleSnapshot]:
        assets = {asset.asset_id: asset for asset in self.list_assets()}
        snapshots: list[LocalModelBundleSnapshot] = []
        for bundle in self.default_bundles():
            installed_assets = sum(1 for asset_id in bundle.asset_ids if assets.get(asset_id) and assets[asset_id].installed)
            snapshots.append(
                LocalModelBundleSnapshot(
                    bundle_id=bundle.bundle_id,
                    display_name=bundle.display_name,
                    description=bundle.description,
                    asset_ids=list(bundle.asset_ids),
                    installed_assets=installed_assets,
                    total_assets=len(bundle.asset_ids),
                )
            )
        return snapshots

    def catalog_snapshot(self) -> LocalModelCatalogSnapshot:
        profiles = self.list_profiles()
        return LocalModelCatalogSnapshot(
            models_dir=self.settings.models_dir.as_posix(),
            available_profiles=sum(1 for profile in profiles if profile.binary_available and profile.enabled),
            configured_profiles=len(profiles),
            profiles=profiles,
            assets=self.list_assets(),
            bundles=self.list_bundles(),
        )

    def capability_manifest(self) -> list[dict[str, object]]:
        return [profile.model_dump(mode="json") for profile in self.list_profiles()]

    async def install(self, request: LocalModelInstallRequest) -> LocalModelInstallResult:
        asset_ids = list(dict.fromkeys(request.asset_ids))
        if request.bundle_id:
            bundle = self._bundle_by_id(request.bundle_id)
            asset_ids = list(dict.fromkeys([*asset_ids, *bundle.asset_ids]))
        if not asset_ids:
            raise ValueError("Provide a bundle_id or at least one asset_id")

        installed_assets: list[LocalModelAssetSnapshot] = []
        skipped_assets: list[LocalModelAssetSnapshot] = []
        for asset_id in asset_ids:
            asset = self._asset_by_id(asset_id)
            destination = self.settings.models_dir / asset.filename
            if destination.exists() and not request.overwrite:
                skipped_assets.append(self._asset_snapshot(asset))
                continue
            await self.proxy.download_file(
                asset.source_url,
                destination,
                sha256=asset.sha256,
                max_bytes=asset.max_bytes,
                executable=asset.executable,
            )
            installed_assets.append(self._asset_snapshot(asset))
        return LocalModelInstallResult(
            bundle_id=request.bundle_id,
            installed_assets=installed_assets,
            skipped_assets=skipped_assets,
        )

    @staticmethod
    def default_assets() -> tuple[ManagedModelAsset, ...]:
        return (
            ManagedModelAsset(
                asset_id="qwen2.5-3b-instruct-q4km",
                display_name="Qwen2.5 3B Instruct Q4_K_M",
                profile_name="llama.cpp-qwen2.5-3b",
                modality="chat",
                filename="Qwen2.5-3B-Instruct-Q4_K_M.gguf",
                source_url="https://huggingface.co/unsloth/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf?download=true",
                description="Recommended small GGUF chat model for phone-hosted llama.cpp inference.",
                max_bytes=3_000_000_000,
            ),
            ManagedModelAsset(
                asset_id="piper-en-us-lessac-medium-onnx",
                display_name="Piper en_US lessac medium voice",
                profile_name="piper-tts",
                modality="tts",
                filename="en_US-lessac-medium.onnx",
                source_url="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx?download=true",
                description="Recommended English Piper voice model for spoken replies.",
                max_bytes=100_000_000,
            ),
            ManagedModelAsset(
                asset_id="piper-en-us-lessac-medium-config",
                display_name="Piper en_US lessac medium config",
                profile_name="piper-tts",
                modality="tts",
                filename="en_US-lessac-medium.onnx.json",
                source_url="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json?download=true",
                description="Companion config for the recommended Piper voice model.",
                max_bytes=1_000_000,
            ),
        )

    @staticmethod
    def default_bundles() -> tuple[ManagedModelBundle, ...]:
        return (
            ManagedModelBundle(
                bundle_id="phone-starter",
                display_name="Phone Starter Bundle",
                description="Installs the recommended phone-sized chat model and Piper voice files into Mordecai's models directory.",
                asset_ids=(
                    "qwen2.5-3b-instruct-q4km",
                    "piper-en-us-lessac-medium-onnx",
                    "piper-en-us-lessac-medium-config",
                ),
            ),
        )

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

    def _asset_snapshot(self, asset: ManagedModelAsset) -> LocalModelAssetSnapshot:
        destination = self.settings.models_dir / asset.filename
        return LocalModelAssetSnapshot(
            asset_id=asset.asset_id,
            display_name=asset.display_name,
            profile_name=asset.profile_name,
            modality=asset.modality,
            filename=asset.filename,
            destination=destination.as_posix(),
            source_url=asset.source_url,
            description=asset.description,
            executable=asset.executable,
            installed=destination.exists(),
            size_mb=(asset.max_bytes / (1024 * 1024)) if asset.max_bytes is not None else None,
            sha256=asset.sha256,
        )

    def _asset_by_id(self, asset_id: str) -> ManagedModelAsset:
        for asset in self.default_assets():
            if asset.asset_id == asset_id:
                return asset
        raise KeyError(f"Unknown local model asset '{asset_id}'")

    def _bundle_by_id(self, bundle_id: str) -> ManagedModelBundle:
        for bundle in self.default_bundles():
            if bundle.bundle_id == bundle_id:
                return bundle
        raise KeyError(f"Unknown local model bundle '{bundle_id}'")

    def _resolve_model_path(self, value: str | None) -> Path | None:
        if not value:
            return None
        raw = Path(value)
        return raw if raw.is_absolute() else (self.settings.models_dir / raw)

    @staticmethod
    def _command_binary(command: str) -> str | None:
        parts = shlex.split(command)
        return parts[0] if parts else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage Mordecai local model assets.")
    parser.add_argument("--install-bundle", dest="bundle_id", help="Install a named local model bundle into the configured models directory.")
    parser.add_argument("--install-root", help="Absolute path to the Mordecai install root to target when resolving backend and data directories.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite already installed model assets.")
    args = parser.parse_args(argv)

    if not args.bundle_id:
        parser.print_help()
        return 1

    from mordecai.config import ensure_state_dirs, get_settings

    if args.install_root:
        install_root = Path(args.install_root).expanduser().resolve()
        os.environ.setdefault("MORDECAI_INSTALL_ROOT", str(install_root))
        os.environ.setdefault("MORDECAI_WORKSPACE_DIR", str((install_root / "backend").resolve()))
        os.environ.setdefault("MORDECAI_DATA_DIR", str((install_root / "data").resolve()))
        os.environ.setdefault("MORDECAI_STATE_DIR", str((install_root / "data" / "state").resolve()))
        os.environ.setdefault("MORDECAI_LOG_DIR", str((install_root / "data" / "logs").resolve()))
        os.environ.setdefault("MORDECAI_CACHE_DIR", str((install_root / "data" / "cache").resolve()))
        os.environ.setdefault("MORDECAI_MODELS_DIR", str((install_root / "data" / "models").resolve()))
        get_settings.cache_clear()

    settings = get_settings()
    ensure_state_dirs(settings)
    service = LocalModelService(settings)
    asyncio.run(service.install(LocalModelInstallRequest(bundle_id=args.bundle_id, overwrite=args.overwrite)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())