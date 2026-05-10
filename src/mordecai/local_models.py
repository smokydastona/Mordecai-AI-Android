from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import shutil
import tarfile
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
    catalog_slug: str | None = None
    runtime_fit: str | None = None
    integration_tier: str | None = None
    requires_operator_approval: bool = False
    install_notes: str | None = None
    archive_format: str | None = None


@dataclass(frozen=True, slots=True)
class ManagedModelBundle:
    bundle_id: str
    display_name: str
    description: str
    asset_ids: tuple[str, ...]
    runtime_fit: str | None = None
    integration_tier: str | None = None
    requires_operator_approval: bool = False
    install_notes: str | None = None
    catalog_slugs: tuple[str, ...] = ()


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
                    runtime_fit=bundle.runtime_fit,
                    integration_tier=bundle.integration_tier,
                    requires_operator_approval=bundle.requires_operator_approval,
                    install_notes=bundle.install_notes,
                    catalog_slugs=list(bundle.catalog_slugs),
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

        if self._install_requires_approval(asset_ids, request.bundle_id) and not request.acknowledge_operator_approval:
            raise PermissionError("Operator approval acknowledgement is required for this install manifest")

        installed_assets: list[LocalModelAssetSnapshot] = []
        skipped_assets: list[LocalModelAssetSnapshot] = []
        extracted_paths: list[str] = []
        for asset_id in asset_ids:
            asset = self._asset_by_id(asset_id)
            destination = self.settings.models_dir / asset.filename
            if destination.exists() and not request.overwrite:
                skipped_assets.append(self._asset_snapshot(asset))
                extracted_paths.extend(self._post_install_paths(asset, destination, extract_if_missing=False))
                continue
            await self.proxy.download_file(
                asset.source_url,
                destination,
                sha256=asset.sha256,
                max_bytes=asset.max_bytes,
                executable=asset.executable,
            )
            extracted_paths.extend(self._post_install_paths(asset, destination, extract_if_missing=True))
            installed_assets.append(self._asset_snapshot(asset))
        return LocalModelInstallResult(
            bundle_id=request.bundle_id,
            installed_assets=installed_assets,
            skipped_assets=skipped_assets,
            approval_acknowledged=request.acknowledge_operator_approval,
            extracted_paths=sorted(dict.fromkeys(extracted_paths)),
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
                source_url="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf?download=true",
                description="Recommended small GGUF chat model for phone-hosted llama.cpp inference.",
                max_bytes=3_000_000_000,
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Chat runtime asset for the phone starter bundle.",
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
                catalog_slug="piper",
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Primary default TTS voice for Mordecai.",
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
                catalog_slug="piper",
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Required Piper config companion file.",
            ),
            ManagedModelAsset(
                asset_id="whispercpp-ggml-base-en",
                display_name="whisper.cpp base.en model",
                profile_name="whisper.cpp-base-en",
                modality="stt",
                filename="ggml-base.en.bin",
                source_url="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
                description="Phone-safe Whisper model in ggml format for whisper.cpp.",
                max_bytes=200_000_000,
                catalog_slug="whisper-cpp",
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Offline ASR model for whisper.cpp integration.",
            ),
            ManagedModelAsset(
                asset_id="whispercpp-silero-vad-v6",
                display_name="whisper.cpp Silero VAD v6",
                profile_name="whisper.cpp-base-en-vad",
                modality="stt",
                filename="ggml-silero-v6.2.0.bin",
                source_url="https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin",
                description="Optional VAD accelerator for whisper.cpp speech segmentation.",
                max_bytes=2_000_000,
                catalog_slug="whisper-cpp",
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Adds local voice activity detection to whisper.cpp.",
            ),
            ManagedModelAsset(
                asset_id="sherpa-onnx-whisper-tiny-en-archive",
                display_name="sherpa-onnx Whisper tiny.en archive",
                profile_name="sherpa-onnx-whisper-tiny-en",
                modality="stt",
                filename="sherpa-onnx-whisper-tiny.en.tar.bz2",
                source_url="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-tiny.en.tar.bz2",
                description="Prebuilt sherpa-onnx Whisper tiny.en archive for mobile-friendly offline ASR.",
                max_bytes=100_000_000,
                catalog_slug="sherpa-onnx",
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Archive download; unpack before wiring into a live sherpa-onnx runtime.",
                archive_format="tar.bz2",
                requires_operator_approval=True,
            ),
            ManagedModelAsset(
                asset_id="sherpa-onnx-silero-vad",
                display_name="sherpa-onnx Silero VAD",
                profile_name="sherpa-onnx-whisper-tiny-en",
                modality="stt",
                filename="silero_vad.onnx",
                source_url="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx",
                description="VAD model used by sherpa-onnx voice pipelines.",
                max_bytes=3_000_000,
                catalog_slug="sherpa-onnx",
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Optional VAD helper for sherpa-onnx speech pipelines.",
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
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Baseline phone bundle with chat and spoken reply support.",
                catalog_slugs=("piper",),
            ),
            ManagedModelBundle(
                bundle_id="voice-asr-whispercpp-phone",
                display_name="Phone ASR Bundle: whisper.cpp",
                description="Installs a whisper.cpp English ASR model plus a matching Silero VAD model for offline phone-grade transcription.",
                asset_ids=(
                    "whispercpp-ggml-base-en",
                    "whispercpp-silero-vad-v6",
                ),
                runtime_fit="phone",
                integration_tier="managed",
                install_notes="Ready for explicit whisper.cpp-based ASR experiments once the whisper.cpp binary is present.",
                catalog_slugs=("whisper-cpp",),
            ),
            ManagedModelBundle(
                bundle_id="voice-asr-sherpa-phone",
                display_name="Phone ASR Bundle: sherpa-onnx",
                description="Downloads a sherpa-onnx Whisper tiny.en archive plus Silero VAD for an offline mobile ASR path.",
                asset_ids=(
                    "sherpa-onnx-whisper-tiny-en-archive",
                    "sherpa-onnx-silero-vad",
                ),
                runtime_fit="phone",
                integration_tier="managed",
                requires_operator_approval=True,
                install_notes="Policy-gated because the archive requires explicit unpacking and runtime wiring before execution.",
                catalog_slugs=("sherpa-onnx",),
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
            catalog_slug=profile.catalog_slug,
            runtime_fit=profile.runtime_fit,
            integration_tier=profile.integration_tier,
            install_asset_ids=list(profile.install_asset_ids or []),
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
            catalog_slug=asset.catalog_slug,
            runtime_fit=asset.runtime_fit,
            integration_tier=asset.integration_tier,
            requires_operator_approval=asset.requires_operator_approval,
            install_notes=asset.install_notes,
            archive_format=asset.archive_format,
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

    def _install_requires_approval(self, asset_ids: list[str], bundle_id: str | None) -> bool:
        if bundle_id is not None and self._bundle_by_id(bundle_id).requires_operator_approval:
            return True
        return any(self._asset_by_id(asset_id).requires_operator_approval for asset_id in asset_ids)

    def _post_install_paths(self, asset: ManagedModelAsset, destination: Path, *, extract_if_missing: bool) -> list[str]:
        if asset.archive_format == "tar.bz2":
            return self._extract_tar_bz2(asset, destination, extract_if_missing=extract_if_missing)
        return []

    def _extract_tar_bz2(self, asset: ManagedModelAsset, archive_path: Path, *, extract_if_missing: bool) -> list[str]:
        extract_root = self._archive_extract_root(asset)
        if extract_root.exists() and extract_if_missing:
            shutil.rmtree(extract_root)
        if extract_root.exists() and not extract_if_missing:
            return [path.as_posix() for path in extract_root.rglob("*") if path.is_file()]
        extract_root.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive_path, mode="r:bz2") as handle:
            members = handle.getmembers()
            self._validate_archive_members(members, extract_root)
            handle.extractall(extract_root, filter="data")

        helper_paths = self._write_archive_helper_files(asset, archive_path, extract_root)
        extracted_files = [path.as_posix() for path in extract_root.rglob("*") if path.is_file()]
        return extracted_files + helper_paths

    @staticmethod
    def _validate_archive_members(members: list[tarfile.TarInfo], extract_root: Path) -> None:
        root = extract_root.resolve()
        for member in members:
            target = (extract_root / member.name).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError(f"Archive member escapes extraction root: {member.name}")

    def _write_archive_helper_files(self, asset: ManagedModelAsset, archive_path: Path, extract_root: Path) -> list[str]:
        helper_paths: list[str] = []
        if asset.asset_id == "sherpa-onnx-whisper-tiny-en-archive":
            manifest_path = extract_root / "mordecai-sherpa-manifest.json"
            manifest = {
                "archive": archive_path.as_posix(),
                "root": extract_root.as_posix(),
                "whisper_encoder": self._stringify_path(self._find_preferred_file(extract_root, ("encoder.int8.onnx", "encoder.onnx"), "encoder", ".onnx")),
                "whisper_decoder": self._stringify_path(self._find_preferred_file(extract_root, ("decoder.int8.onnx", "decoder.onnx"), "decoder", ".onnx")),
                "tokens": self._stringify_path(self._find_preferred_file(extract_root, ("tokens.txt",), "tokens", ".txt")),
                "test_wavs": sorted(path.as_posix() for path in extract_root.rglob("*.wav")),
            }
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            helper = extract_root / "mordecai-sherpa-setup.txt"
            helper.write_text(
                "\n".join(
                    [
                        "Sherpa-onnx archive extracted by Mordecai.",
                        f"Archive: {archive_path.as_posix()}",
                        f"Root: {extract_root.as_posix()}",
                        "The extracted manifest is ready for the voice runtime's sherpa-onnx execution path.",
                        f"Manifest: {manifest_path.as_posix()}",
                        f"Whisper encoder: {manifest['whisper_encoder'] or 'not auto-detected'}",
                        f"Whisper decoder: {manifest['whisper_decoder'] or 'not auto-detected'}",
                        f"Tokens: {manifest['tokens'] or 'not auto-detected'}",
                    ]
                ),
                encoding="utf-8",
            )
            helper_paths.append(manifest_path.as_posix())
            helper_paths.append(helper.as_posix())
        return helper_paths

    @staticmethod
    def _find_first_matching_file(root: Path, *needles: str) -> Path | None:
        lowered_needles = tuple(needle.lower() for needle in needles)
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lowered = path.name.lower()
            if all(needle in lowered for needle in lowered_needles):
                return path
        return None

    def _archive_extract_root(self, asset: ManagedModelAsset) -> Path:
        suffix = f".{asset.archive_format}" if asset.archive_format else ""
        directory_name = asset.filename.removesuffix(suffix) if suffix else asset.filename
        return self.settings.models_dir / directory_name

    def _find_preferred_file(self, root: Path, preferred_suffixes: tuple[str, ...], *fallback_needles: str) -> Path | None:
        lowered_suffixes = tuple(value.lower() for value in preferred_suffixes)
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            lowered = path.name.lower()
            if any(lowered.endswith(suffix) for suffix in lowered_suffixes):
                return path
        return self._find_first_matching_file(root, *fallback_needles)

    @staticmethod
    def _stringify_path(path: Path | None) -> str | None:
        return path.as_posix() if path is not None else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage Mordecai local model assets.")
    parser.add_argument("--install-bundle", dest="bundle_id", help="Install a named local model bundle into the configured models directory.")
    parser.add_argument("--install-root", help="Absolute path to the Mordecai install root to target when resolving backend and data directories.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite already installed model assets.")
    parser.add_argument("--acknowledge-operator-approval", action="store_true", help="Acknowledge operator approval for gated install manifests.")
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
    asyncio.run(
        service.install(
            LocalModelInstallRequest(
                bundle_id=args.bundle_id,
                overwrite=args.overwrite,
                acknowledge_operator_approval=args.acknowledge_operator_approval,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())