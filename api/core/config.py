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

    # Voice/NLU (§7.3) — Groq для nlu_service (b9); пусто → локальный regex-fallback.
    groq_api_key: str | None = None
    whisper_model: str = "large-v3"
    whisper_device: str = "cpu"
    # whisper_compute_type: CTranslate2 compute-тип. "default" → авто под железо
    #   (int8 на x86 AVX-512, float16 на ARM/Apple Silicon). Можно форсировать:
    #   "int8", "int8_float16", "float16", "float32".
    whisper_compute_type: str = "default"
    # whisper_cpu_threads: 0 → авто (CTranslate2 сам определяет число потоков).
    #   Форсировать: 8 для 12-ядерного M4 Pro, 4-8 для большинства CPU.
    whisper_cpu_threads: int = 0
    # whisper_num_workers: параллельная обработка сегментов (≥2 для многоядерных CPU).
    whisper_num_workers: int = 1

    # Performance: DuckDB PRAGMAs (§perf).
    # duckdb_threads: 0 → авто (C++ ядро DuckDB само определяет число потоков).
    #   Форсировать: 8 для M4 Pro, 4-8 для большинства CPU.
    duckdb_threads: int = 0
    # duckdb_memory_limit_mb: 0 → без лимита (DuckDB сам управляет памятью).
    #   На 24 GB M4 Pro рекомендуется 4096 (4 GB), чтобы не вытеснить Whisper.
    duckdb_memory_limit_mb: int = 0

    # Performance: Uvicorn / FastAPI (§perf).
    # api_workers: число worker-процессов uvicorn. 0 → авто = cpu_count.
    #   На 12-ядерном M4 Pro рекомендуется 4-6 (не все ядра — часть под DuckDB/OS).
    api_workers: int = 0

    # Security baseline (§8.9, b26). Дефолт OFF — нулевой blast-radius на демо/тесты.
    # Включается ТОЛЬКО на старте процесса сервера через env `SKAI_SECURITY_ENABLED=true`
    # (голая `SECURITY_ENABLED` не читается — нужен префикс SKAI_). Middleware читает
    # `settings.security_enabled` на каждом запросе, поэтому значение не кэшируется на импорте.
    security_enabled: bool = False


settings = Settings()
