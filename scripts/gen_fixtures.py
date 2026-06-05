#!/usr/bin/env python3
"""Синхронизация фронт-фикстур с моком инцидентов (idea: фикстуры не расходятся с `data/mock`).

Источник формы — `data/mock/incidents.py` (`INCIDENTS`). Канон-маппинг имён по
00-CONTRACT.md §3.1:  score→risk_score · event_source→source · alarm_type_label→alarm_label_ru.

⚠️  Курируемый `web/src/api/fixtures.ts` принадлежит f3 и содержит поля обогащения
(driver_phone, driver_region, confidence, cam_extra, …), которых в моке НЕТ. Поэтому
скрипт НИКОГДА не перезаписывает `fixtures.ts` напрямую — иначе обогащение будет потеряно.

Режимы:
    python scripts/gen_fixtures.py              # check: сверка мока с fixtures.ts (дрейф)
    python scripts/gen_fixtures.py --strict     # check + ненулевой код выхода при дрейфе
    python scripts/gen_fixtures.py --write       # запись sidecar web/src/api/fixtures.generated.ts

Согласовано с f3: `--write` пишет ОТДЕЛЬНЫЙ файл-ориентир, а не курируемые фикстуры.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MOCK = _ROOT / "data" / "mock" / "incidents.py"
_FIXTURES = _ROOT / "web" / "src" / "api" / "fixtures.ts"
_SIDECAR = _ROOT / "web" / "src" / "api" / "fixtures.generated.ts"

# Канон-маппинг legacy-имён мока → имена контракта (§3.1).
CANON = {
    "score": "risk_score",
    "event_source": "source",
    "alarm_type_label": "alarm_label_ru",
}


def load_mock_incidents(path: Path) -> list[dict]:
    """Загружает `INCIDENTS` из data/mock/incidents.py по файловому пути (без пакетов)."""
    spec = importlib.util.spec_from_file_location("_skai_mock_incidents", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не удалось загрузить мок: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.INCIDENTS)


def canon(inc: dict) -> dict:
    """Применяет канон-маппинг имён и нормализует камеры под контракт Camera."""
    out: dict = {CANON.get(k, k): v for k, v in inc.items()}
    if "cameras" in out:
        out["cameras"] = [
            {
                **cam,
                "offline_from": cam.get("offline_from"),
                "offline_to": cam.get("offline_to"),
            }
            for cam in out["cameras"]
        ]
    return out


def to_ts(value, indent: int = 0) -> str:
    """Рендерит Python-значение как TS-литерал (true/false/null, объекты, массивы)."""
    pad = "  " * indent
    pad_in = "  " * (indent + 1)
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        items = ",\n".join(pad_in + to_ts(v, indent + 1) for v in value)
        return "[\n" + items + "\n" + pad + "]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = ",\n".join(f"{pad_in}{k}: {to_ts(v, indent + 1)}" for k, v in value.items())
        return "{\n" + items + "\n" + pad + "}"
    raise TypeError(f"Неподдерживаемый тип: {type(value)!r}")


def render_sidecar(incidents: list[dict]) -> str:
    """Генерирует TS-модуль-ориентир с канон-маппленными инцидентами мока."""
    mapped = [canon(inc) for inc in incidents]
    body = ",\n  ".join(to_ts(inc, 1) for inc in mapped)
    return (
        "// СГЕНЕРИРОВАНО scripts/gen_fixtures.py — не редактировать вручную.\n"
        "// Канон-маппинг имён мока (§3.1). Это файл-ОРИЕНТИР для сверки с f3-фикстурами,\n"
        "// а НЕ замена web/src/api/fixtures.ts (там есть поля обогащения, которых нет в моке).\n\n"
        "export const MOCK_INCIDENTS = [\n  " + body + ",\n]\n"
    )


def check_drift(incidents: list[dict], fixtures_text: str) -> list[str]:
    """Эвристическая сверка: ключевые канон-поля мока присутствуют в fixtures.ts."""
    issues: list[str] = []
    for inc in incidents:
        mapped = canon(inc)
        iid = mapped["id"]
        if iid not in fixtures_text:
            issues.append(f"{iid}: нет в fixtures.ts")
            continue
        for field in ("alarm_label_ru", "source", "risk_score"):
            needle = str(mapped[field])
            if needle not in fixtures_text:
                issues.append(f"{iid}: {field}={mapped[field]!r} не найден в fixtures.ts")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync фронт-фикстур с data/mock/incidents.py")
    parser.add_argument("--write", action="store_true", help="записать sidecar fixtures.generated.ts")
    parser.add_argument("--strict", action="store_true", help="ненулевой код выхода при дрейфе")
    parser.add_argument("-o", "--output", type=Path, default=_SIDECAR, help="путь sidecar при --write")
    args = parser.parse_args(argv)

    incidents = load_mock_incidents(_MOCK)

    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_sidecar(incidents), encoding="utf-8")
        rel = args.output.relative_to(_ROOT) if args.output.is_relative_to(_ROOT) else args.output
        print(f"sidecar → {rel} ({len(incidents)} инцидентов)")
        return 0

    if not _FIXTURES.exists():
        print(f"fixtures.ts не найден: {_FIXTURES} — пропускаю сверку")
        return 0

    issues = check_drift(incidents, _FIXTURES.read_text(encoding="utf-8"))
    if not issues:
        print(f"OK · мок ({len(incidents)} инц.) согласован с fixtures.ts по ключевым полям")
        return 0
    print(f"ДРЕЙФ ({len(issues)}):")
    for line in issues:
        print(f"  - {line}")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
