#!/usr/bin/env python3
"""Скелет генератора `CURRENT_STATUS.md` (w3-19 · 00-CONTRACT §8.9).

Единый источник истины «реализовано vs план» — против дрейфа
README ↔ RUNBOOK ↔ contract. Перечень роутеров и SQL-объектов берётся
ИЗ ФАКТА (`api/routers/*.py`, `api/sql/*.sql`), а не из README.

Статус каждого пункта вычисляется детерминированно с диска:
    ✅ реализовано · 🟡 заглушка (501) / в работе · ⬜ план (файла ещё нет).

Вывод детерминированный (сорт по id) и идемпотентный: повторный запуск даёт
ПОБАЙТОВО идентичный файл — без меток времени/`random` (§9 «детерминизм»).

    python scripts/gen_status.py            # → CURRENT_STATUS.md (корень репо)
    python scripts/gen_status.py -o out.md  # произвольный путь

Расширяется t5 (Волна 4.3): статус сверяется с РЕАЛЬНЫМ прогоном pytest/vitest,
а не только с наличием файла на диске (✅ требует зелёных тестов).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ROUTERS_DIR = _ROOT / "api" / "routers"
_SQL_DIR = _ROOT / "api" / "sql"
_DEFAULT_OUT = _ROOT / "CURRENT_STATUS.md"

# Маркеры статуса.
DONE, WIP, PLAN = "✅", "🟡", "⬜"

# Признак 501-заглушки в роутере (Волна 3 поднимает fuel/sensors/navigation).
_STUB_RE = re.compile(r"\b501\b|NotImplemented|not_implemented")
# `prefix="/api/..."` из объявления APIRouter(...).
_PREFIX_RE = re.compile(r"""prefix\s*=\s*["']([^"']+)["']""")
# CREATE [OR REPLACE] (VIEW|TABLE) [IF NOT EXISTS] "name" — имя SQL-объекта из факта.
_SQL_OBJ_RE = re.compile(
    r'create\s+(?:or\s+replace\s+)?(?:view|table)\s+(?:if\s+not\s+exists\s+)?"?([a-z0-9_]+)"?',
    re.IGNORECASE,
)

# Закрепление вех (скаффолд t5): «какой пункт к какой вехе».
# Перечень всё равно идёт из факта; здесь — только принадлежность секции.
# id, заголовок, {роутеры: [...], sql: [...]}.
SECTIONS: list[tuple[str, str, dict[str, list[str]]]] = [
    (
        "P0",
        "Ядро MVP — инциденты · отчёты · парк",
        {
            "routers": ["incidents", "reports", "vehicles", "actions"],
            "sql": ["v_incidents", "v_driver_report", "v_fleet", "v_vehicle"],
        },
    ),
    (
        "P1",
        "Мониторинг и реакция — алерты · заявки · рейсы",
        {"routers": ["alerts", "tickets", "trips"], "sql": []},
    ),
    (
        "P2",
        "РЭБ и саботаж",
        {"routers": ["sabotage", "reb"], "sql": ["v_sabotage", "v_reb"]},
    ),
    (
        "Волна 3",
        "Тёмные данные — fuel · sensors · navigation (подъём из 501)",
        {"routers": ["fuel", "sensors", "navigation"], "sql": []},
    ),
    (
        "Волна 4",
        "AI Ops & Trust (каркас w3-16…19; логика — Волна 4.3)",
        {"routers": ["metrics"], "sql": ["ai_metric_events"]},
    ),
]


class Router:
    """Факт о роутере с диска: имя модуля, prefix, признак 501-заглушки."""

    def __init__(self, name: str, prefix: str | None, is_stub: bool) -> None:
        self.name = name
        self.prefix = prefix
        self.is_stub = is_stub

    @property
    def status(self) -> str:
        return WIP if self.is_stub else DONE


def discover_routers() -> dict[str, Router]:
    """`{имя: Router}` для `api/routers/*.py` (кроме `__init__`). Факт с диска."""
    found: dict[str, Router] = {}
    if not _ROUTERS_DIR.is_dir():
        return found
    for path in sorted(_ROUTERS_DIR.glob("*.py")):
        if path.stem == "__init__":
            continue
        text = path.read_text(encoding="utf-8")
        prefix_match = _PREFIX_RE.search(text)
        found[path.stem] = Router(
            name=path.stem,
            prefix=prefix_match.group(1) if prefix_match else None,
            is_stub=bool(_STUB_RE.search(text)),
        )
    return found


def discover_sql_objects() -> set[str]:
    """Множество имён SQL-вью/таблиц из `CREATE ...` в `api/sql/*.sql`. Факт с диска."""
    names: set[str] = set()
    if not _SQL_DIR.is_dir():
        return names
    for path in sorted(_SQL_DIR.glob("*.sql")):
        for match in _SQL_OBJ_RE.finditer(path.read_text(encoding="utf-8")):
            names.add(match.group(1).lower())
    return names


def _router_line(name: str, routers: dict[str, Router]) -> str:
    router = routers.get(name)
    if router is None:
        return f"- {PLAN} `{name}` — роутер (план, файла нет)"
    prefix = f" (`{router.prefix}`)" if router.prefix else ""
    note = " — заглушка 501" if router.is_stub else ""
    return f"- {router.status} `{name}`{prefix}{note}"


def _sql_line(name: str, sql_objects: set[str]) -> str:
    mark = DONE if name in sql_objects else PLAN
    note = "" if name in sql_objects else " — план, объекта нет"
    return f"- {mark} `{name}`{note}"


def render(routers: dict[str, Router], sql_objects: set[str]) -> str:
    """Собирает Markdown-документ из фактов диска + закрепления вех."""
    lines: list[str] = [
        "# CURRENT_STATUS — реализовано vs план",
        "",
        "> ⚠️ **Не редактировать вручную.** Источник — `scripts/gen_status.py` "
        "(00-CONTRACT §8.9).",
        "> Перечень роутеров/таблиц берётся из факта (`api/routers`, `api/sql`), не из README.",
        f"> Статус: {DONE} реализовано · {WIP} заглушка (501)/в работе · {PLAN} план (файла нет).",
        "> Скелет (w3-19); t5 доводит до сверки с прогоном тестов (pytest/vitest).",
        "",
    ]

    # ── Сводка (детерминированные счётчики) ──────────────────────
    r_done = sum(1 for r in routers.values() if not r.is_stub)
    r_stub = sum(1 for r in routers.values() if r.is_stub)
    lines += [
        "## Сводка",
        "",
        f"- Роутеры (`api/routers`): **{len(routers)}** "
        f"({DONE} {r_done} · {WIP} {r_stub})",
        f"- SQL-объекты (`api/sql`): **{len(sql_objects)}** ({DONE} {len(sql_objects)})",
        "",
    ]

    # ── Секции вех ───────────────────────────────────────────────
    for sid, title, members in SECTIONS:
        lines.append(f"## {sid} · {title}")
        lines.append("")
        for name in sorted(members.get("routers", [])):
            lines.append(_router_line(name, routers))
        for name in sorted(members.get("sql", [])):
            lines.append(_sql_line(name, sql_objects))
        lines.append("")

    # ── Не закреплено за вехой (анти-«тихая потеря» файла с диска) ─
    assigned_routers = {n for _, _, m in SECTIONS for n in m.get("routers", [])}
    assigned_sql = {n for _, _, m in SECTIONS for n in m.get("sql", [])}
    extra_routers = sorted(set(routers) - assigned_routers)
    extra_sql = sorted(sql_objects - assigned_sql)
    if extra_routers or extra_sql:
        lines.append("## Не закреплено за вехой")
        lines.append("")
        for name in extra_routers:
            lines.append(_router_line(name, routers))
        for name in extra_sql:
            lines.append(_sql_line(name, sql_objects))
        lines.append("")

    # ── Инвентарь (чистый факт с диска, сорт по id) ──────────────
    lines.append("## Инвентарь (факт с диска)")
    lines.append("")
    lines.append("### Роутеры (`api/routers/*.py`)")
    lines.append("")
    for name in sorted(routers):
        lines.append(_router_line(name, routers))
    lines.append("")
    lines.append("### SQL-объекты (`api/sql/*.sql`)")
    lines.append("")
    for name in sorted(sql_objects):
        lines.append(f"- {DONE} `{name}`")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def generate(out_path: Path) -> Path:
    """Пишет `CURRENT_STATUS.md`. Возвращает путь."""
    content = render(discover_routers(), discover_sql_objects())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Генератор CURRENT_STATUS.md из факта (api/routers, api/sql)."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_DEFAULT_OUT,
        help="путь к выходному файлу (default: CURRENT_STATUS.md в корне)",
    )
    args = parser.parse_args(argv)
    out = generate(args.output)
    rel = out.relative_to(_ROOT) if out.is_relative_to(_ROOT) else out
    print(f"CURRENT_STATUS → {rel} ({out.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
