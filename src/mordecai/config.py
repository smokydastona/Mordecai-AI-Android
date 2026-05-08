from functools import lru_cache
from pathlib import Path

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
    enable_advanced_self_improvement: bool = False
    enable_daemon_mode: bool = False
    allow_git_push: bool = False
    auto_apply_improvements: bool = False
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
            "huggingface.co",
            "pypi.org",
            "docs.python.org",
            "duckduckgo.com",
            "html.duckduckgo.com",
        ]
    )

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        workspace_dir = self._normalize_path(self.workspace_dir) if self.workspace_dir else Path.cwd().resolve()
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
