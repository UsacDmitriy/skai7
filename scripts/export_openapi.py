#!/usr/bin/env python3
"""Экспорт OpenAPI-схемы FastAPI-приложения в docs/openapi.json.

Импортирует `api.main:app` (без запуска uvicorn-сервера) и сериализует
`app.openapi()`. БД при этом не нужна: схема строится из роутов, lifespan не
вызывается. Полезно для документации и генерации клиентов.

Запуск:
    python scripts/export_openapi.py               # → docs/openapi.json
    python scripts/export_openapi.py -o some.json
    make openapi
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Корень проекта = родитель каталога scripts/ — добавляем в sys.path,
# чтобы `import api.main` работал при запуске скрипта напрямую.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def export(out_path: Path) -> Path:
    """Сериализует OpenAPI-схему приложения в `out_path`, создавая каталоги."""
    from api.main import app  # импорт после настройки sys.path

    schema = app.openapi()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Экспорт OpenAPI-схемы FastAPI в JSON.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_ROOT / "docs" / "openapi.json",
        help="Путь к выходному файлу (default: docs/openapi.json)",
    )
    args = parser.parse_args(argv)
    out = export(args.output)
    rel = out.relative_to(_ROOT) if out.is_relative_to(_ROOT) else out
    print(f"OpenAPI → {rel} ({out.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
