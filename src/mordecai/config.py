from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MORDECAI_", env_file=".env", extra="ignore")

    app_name: str = "Mordecai"
    user_name: str = "Jarin"
    environment: str = "development"
    install_root: Path | None = None
    workspace_dir: Path | None = None
    data_dir: Path | None = None
    state_dir: Path | None = None
    log_dir: Path | None = None
    cache_dir: Path | None = None
    models_dir: Path | None = None
    avatar_assets_dir: Path | None = None
    default_provider: str = "rule-based"
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    wake_words: list[str] = Field(default_factory=lambda: ["Mordecai", "Mori", "Cai"])
    allowed_android_packages: list[str] = Field(default_factory=lambda: ["com.termux"])
    max_requests_per_minute: int = 30
    max_cpu_percent: float = 85.0
    max_memory_mb: int = 768
    max_log_entries: int = 500
    proxy_timeout_seconds: float = 20.0
    service_host: str = "127.0.0.1"
    service_port: int = 8000
    mode: str = "mode-a"
    enable_android_control: bool = False
    enable_mode_b: bool = False
    enable_home_automation: bool = False
    enable_advanced_self_improvement: bool = False
    enable_daemon_mode: bool = False
    allow_git_push: bool = False
    auto_apply_improvements: bool = False
    home_automation_mode: str = "both"
    home_automation_require_confirmation: bool = True
    home_automation_timeout_seconds: float = 10.0
    home_assistant_base_url: str | None = None
    home_assistant_access_token: str | None = None
    home_assistant_allowed_hosts: list[str] = Field(default_factory=list)
    home_assistant_allowed_entity_ids: list[str] = Field(default_factory=list)
    home_assistant_allowed_scene_ids: list[str] = Field(default_factory=list)
    philips_hue_bridge_url: str | None = None
    philips_hue_application_key: str | None = None
    philips_hue_allowed_hosts: list[str] = Field(default_factory=list)
    philips_hue_allowed_light_ids: list[str] = Field(default_factory=list)
    philips_hue_allowed_scene_ids: list[str] = Field(default_factory=list)
    system_prompt_path: Path | None = None
    allowed_domains: list[str] = Field(
        default_factory=lambda: [
            "api.duckduckgo.com",
            "api.github.com",
            "api.openai.com",
            "api.anthropic.com",
            "generativelanguage.googleapis.com",
            "openrouter.ai",
            "github.com",
            "hf.co",
            "huggingface.co",
            "cas-bridge.xethub.hf.co",
            "cdn-lfs.hf.co",
            "cdn-lfs-us-1.hf.co",
            "cdn-lfs-eu-1.hf.co",
            "pypi.org",
            "docs.python.org",
            "duckduckgo.com",
            "html.duckduckgo.com",
        ]
    )

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        self.home_automation_mode = self._normalize_home_automation_mode(self.home_automation_mode)
        self.home_assistant_base_url = self._normalize_url(self.home_assistant_base_url)
        self.philips_hue_bridge_url = self._normalize_url(self.philips_hue_bridge_url)
        self.home_assistant_allowed_hosts = self._normalize_host_list(self.home_assistant_allowed_hosts)
        self.philips_hue_allowed_hosts = self._normalize_host_list(self.philips_hue_allowed_hosts)
        self.home_assistant_allowed_entity_ids = self._normalize_identifier_list(self.home_assistant_allowed_entity_ids)
        self.home_assistant_allowed_scene_ids = self._normalize_identifier_list(self.home_assistant_allowed_scene_ids)
        self.philips_hue_allowed_light_ids = self._normalize_identifier_list(self.philips_hue_allowed_light_ids)
        self.philips_hue_allowed_scene_ids = self._normalize_identifier_list(self.philips_hue_allowed_scene_ids)
        self.allowed_domains = self._merge_allowed_domains(
            self.allowed_domains,
            self.home_assistant_allowed_hosts,
            self.philips_hue_allowed_hosts,
        )
        workspace_dir = self._normalize_path(self.workspace_dir) if self.workspace_dir else Path.cwd().resolve()
        workspace_dir.mkdir(parents=True, exist_ok=True)
        install_root = self._normalize_path(self.install_root) if self.install_root else self._default_install_root(workspace_dir)

        if self.data_dir:
            data_dir = self._normalize_path(self.data_dir)
        elif self.state_dir:
            state_dir_hint = self._normalize_path(self.state_dir)
            data_dir = state_dir_hint.parent if state_dir_hint.name == "state" else state_dir_hint
        elif workspace_dir.name == "backend":
            data_dir = install_root / "data"
        else:
            data_dir = workspace_dir / ".mordecai"

        if self.state_dir:
            state_dir = self._normalize_path(self.state_dir)
        else:
            state_dir = data_dir / "state" if data_dir.name == "data" else data_dir

        self.install_root = install_root
        self.workspace_dir = workspace_dir
        self.data_dir = data_dir
        self.state_dir = state_dir
        self.log_dir = self._normalize_path(self.log_dir) if self.log_dir else data_dir / "logs"
        self.cache_dir = self._normalize_path(self.cache_dir) if self.cache_dir else data_dir / "cache"
        self.models_dir = self._normalize_path(self.models_dir) if self.models_dir else data_dir / "models"
        self.system_prompt_path = (
            self._normalize_path(self.system_prompt_path)
            if self.system_prompt_path
            else workspace_dir / "prompts" / "system_prompt.txt"
        )
        default_avatar_assets_dir = workspace_dir / "assets" / "avatar"
        repo_avatar_assets_dir = Path(__file__).resolve().parents[2] / "assets" / "avatar"
        self.avatar_assets_dir = (
            self._normalize_path(self.avatar_assets_dir)
            if self.avatar_assets_dir
            else (default_avatar_assets_dir if default_avatar_assets_dir.exists() else repo_avatar_assets_dir)
        )
        return self

    @staticmethod
    def _normalize_path(path: Path) -> Path:
        return Path(path).expanduser().resolve()

    @staticmethod
    def _normalize_url(url: str | None) -> str | None:
        if url is None:
            return None
        normalized = url.strip().rstrip("/")
        return normalized or None

    @staticmethod
    def _normalize_host_list(hosts: list[str]) -> list[str]:
        normalized: list[str] = []
        for host in hosts:
            value = host.strip().lower()
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    @staticmethod
    def _normalize_identifier_list(values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            cleaned = value.strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    @staticmethod
    def _normalize_home_automation_mode(mode: str) -> str:
        normalized = mode.strip().lower()
        allowed = {"home-assistant", "philips-hue", "both"}
        if normalized not in allowed:
            raise ValueError(f"Unsupported home automation mode: {mode}")
        return normalized

    @staticmethod
    def _merge_allowed_domains(existing: list[str], *host_lists: list[str]) -> list[str]:
        merged: list[str] = []
        for entry in existing:
            normalized = entry.strip().lower()
            if normalized and normalized not in merged:
                merged.append(normalized)
        for host_list in host_lists:
            for host in host_list:
                normalized = host.strip().lower()
                if normalized and normalized not in merged:
                    merged.append(normalized)
        return merged

    def configured_home_automation_backends(self) -> tuple[str, ...]:
        if not self.enable_home_automation:
            return ()
        backends: list[str] = []
        if self.home_automation_mode in {"home-assistant", "both"} and self.home_assistant_base_url and self.home_assistant_access_token:
            backends.append("home-assistant")
        if self.home_automation_mode in {"philips-hue", "both"} and self.philips_hue_bridge_url and self.philips_hue_application_key:
            backends.append("philips-hue")
        return tuple(backends)

    def configured_home_automation_hosts(self) -> tuple[str, ...]:
        hosts: list[str] = []
        for url in (self.home_assistant_base_url, self.philips_hue_bridge_url):
            if not url:
                continue
            hostname = urlparse(url).hostname
            if hostname and hostname not in hosts:
                hosts.append(hostname)
        return tuple(hosts)

    @staticmethod
    def _default_install_root(workspace_dir: Path) -> Path:
        if workspace_dir.name == "backend":
            return workspace_dir.parent.resolve()
        return workspace_dir.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def ensure_state_dirs(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    (settings.state_dir / "backups").mkdir(parents=True, exist_ok=True)
    (settings.state_dir / "candidates").mkdir(parents=True, exist_ok=True)
