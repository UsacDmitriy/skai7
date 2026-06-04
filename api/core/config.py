"""
Application settings (pydantic-settings).

Paths are resolved relative to the project root (the backend worktree root),
which is two levels above this file: api/core/config.py -> api -> <root>.
Override any value via environment variables (prefix SKAI_), e.g. SKAI_DB_PATH=...
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# api/core/config.py -> api/core -> api -> <project_root>
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration. All paths default relative to project_root."""

    model_config = SettingsConfigDict(env_prefix="SKAI_", extra="ignore")

    project_root: Path = _PROJECT_ROOT
    datasets_dir: Path = _PROJECT_ROOT / "datasets" / "ready"
    db_path: Path = _PROJECT_ROOT / "data" / "skai.duckdb"
    media_dir: Path = _PROJECT_ROOT / "datasets" / "media"
    output_dir: Path = _PROJECT_ROOT / "output"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


settings = Settings()
