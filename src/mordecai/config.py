from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MORDECAI_", env_file=".env", extra="ignore")

    app_name: str = "Mordecai"
    user_name: str = "Jarin"
    environment: str = "development"
    workspace_dir: Path = Field(default_factory=lambda: Path.cwd())
    state_dir: Path = Field(default_factory=lambda: Path.cwd() / ".mordecai")
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
    enable_android_control: bool = False
    allow_git_push: bool = False
    auto_apply_improvements: bool = False
    system_prompt_path: Path = Field(default_factory=lambda: Path.cwd() / "prompts" / "system_prompt.txt")
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def ensure_state_dirs(settings: Settings) -> None:
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    (settings.state_dir / "backups").mkdir(parents=True, exist_ok=True)
    (settings.state_dir / "candidates").mkdir(parents=True, exist_ok=True)
