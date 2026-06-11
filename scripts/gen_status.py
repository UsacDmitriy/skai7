#!/usr/bin/env python3
"""Генератор `CURRENT_STATUS.md` (t5 · 00-CONTRACT §8.9).

Единый источник истины «реализовано vs план» — против дрейфа
README ↔ RUNBOOK ↔ contract. Перечень роутеров и SQL-объектов берётся
ИЗ ФАКТА (`api/routers/*.py`, `api/sql/*.sql`), а не из README.

Статус каждого пункта вычисляется детерминированно с диска **и сверяется с
последним прогоном тестов** (JUnit-отчёты pytest/vitest в `reports/`):

    ✅ реализовано (файл есть · тесты зелёные)
    🟡 заглушка (501) / в работе
    ❌ файл есть, но связанные тесты падают в последнем прогоне
    ⬜ план (файла ещё нет)

«✅ требует зелёных тестов»: если последний прогон pytest имел падения,
относящиеся к роутеру/SQL-объекту, пункт понижается до ❌ (даже если файл есть).
Сверка идёт по последнему прогону, а не «на лету» — генератор тесты НЕ запускает.

Вывод детерминированный (сорт по id) и идемпотентный: повторный запуск на том же
состоянии диска (исходники + те же отчёты) даёт ПОБАЙТОВО идентичный файл — без
меток времени/`random` (§9 «детерминизм»). Метки времени из JUnit НЕ рендерятся.

    python scripts/gen_status.py                 # → CURRENT_STATUS.md (корень репо)
    python scripts/gen_status.py -o out.md       # произвольный путь
    python scripts/gen_status.py -r reports       # каталог JUnit-отчётов

Отчёты готовит `scripts/check.sh` / CI:
    pytest -q api/tests --junitxml=reports/pytest-junit.xml
    (cd web && npx vitest run --reporter=junit --outputFile=../reports/vitest-junit.xml)
Если отчётов нет — генератор не падает: статус считается только по диску, а в шапке
проставляется «прогон тестов не найден».
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.etree import ElementTree as ET

_ROOT = Path(__file__).resolve().parents[1]
_ROUTERS_DIR = _ROOT / "api" / "routers"
_SQL_DIR = _ROOT / "api" / "sql"
_DEFAULT_OUT = _ROOT / "CURRENT_STATUS.md"
_DEFAULT_REPORTS = _ROOT / "reports"

# Имена JUnit-отчётов в каталоге reports/ (пишет scripts/check.sh / CI).
_PYTEST_REPORT = "pytest-junit.xml"
_VITEST_REPORT = "vitest-junit.xml"

# Маркеры статуса.
DONE, WIP, FAIL, PLAN = "✅", "🟡", "❌", "⬜"

# Признак 501-заглушки в роутере (Волна 3 поднимает fuel/sensors/navigation).
_STUB_RE = re.compile(r"\b501\b|NotImplemented|not_implemented")
# `prefix="/api/..."` из объявления APIRouter(...).
_PREFIX_RE = re.compile(r"""prefix\s*=\s*["']([^"']+)["']""")
# CREATE [OR REPLACE] (VIEW|TABLE) [IF NOT EXISTS] "name" — имя SQL-объекта из факта.
_SQL_OBJ_RE = re.compile(
    r'create\s+(?:or\s+replace\s+)?(?:view|table)\s+(?:if\s+not\s+exists\s+)?"?([a-z0-9_]+)"?',
    re.IGNORECASE,
)
# `-- ...` до конца строки — комментарии не должны давать ложных объектов
# (напр. строка-документация «CREATE TABLE IF NOT EXISTS — …» → фантомный `if`).
_SQL_COMMENT_RE = re.compile(r"--[^\n]*")

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
        "Тёмные данные — fuel · sensors · navigation · здоровье парка",
        {
            "routers": ["fuel", "sensors", "navigation", "fleet_health"],
            "sql": ["v_fuel", "v_sensors", "v_nav_problem", "v_fleet_health"],
        },
    ),
    (
        "Волна 4",
        "AI Ops & Trust — копилот · прогноз · усталость · сцена · риск-зоны",
        {
            "routers": ["copilot", "forecast", "fatigue", "scene", "zones"],
            # v_risk_zones — НЕ создаётся в SQL (DBSCAN в zones_service.py;
            # 32_v_risk_zones.sql — документальный якорь). Покрыт роутером `zones`.
            "sql": ["incident_scene", "incident_weather", "ai_metric_events"],
        },
    ),
]


class Router:
    """Факт о роутере с диска: имя модуля, prefix, признак 501-заглушки."""

    def __init__(self, name: str, prefix: str | None, is_stub: bool) -> None:
        self.name = name
        self.prefix = prefix
        self.is_stub = is_stub


class TestRun:
    """Сводка последнего прогона JUnit: счётчики + множество «упавших» имён.

    `failed_tokens` — нормализованные строки (classname + name) тех кейсов, что
    упали/завершились ошибкой. По ним `feature_failed()` решает, относится ли
    падение к конкретному роутеру/SQL-объекту (по границе слова).
    """

    def __init__(self) -> None:
        self.found = False  # был ли хоть один отчёт прочитан
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.skipped = 0
        self.failed_tokens: set[str] = set()

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors + self.skipped

    @property
    def green(self) -> bool:
        """Зелёный прогон = были тесты и ни одного падения/ошибки."""
        return self.found and self.failed == 0 and self.errors == 0

    def feature_failed(self, name: str) -> bool:
        """True, если хоть один упавший кейс ссылается на `name` (граница слова)."""
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(name.lower())}(?![a-z0-9])")
        return any(pattern.search(token) for token in self.failed_tokens)


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
        text = _SQL_COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
        for match in _SQL_OBJ_RE.finditer(text):
            names.add(match.group(1).lower())
    return names


def _ingest_junit(path: Path, run: TestRun) -> None:
    """Влить один JUnit-XML в `run`: счётчики + токены упавших кейсов.

    Понимает форматы pytest (`<testsuite>` с `classname`) и vitest
    (`<testsuites>`→`<testsuite name=файл>`→`<testcase name=...>`). Битый/пустой
    отчёт молча игнорируется (статус останется по диску).
    """
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return
    run.found = True
    suites = root.iter("testsuite")
    for suite in suites:
        suite_name = suite.get("name", "")
        for case in suite.findall("testcase"):
            classname = case.get("classname") or suite_name
            name = case.get("name", "")
            failure = case.find("failure") is not None
            error = case.find("error") is not None
            skipped = case.find("skipped") is not None
            if failure or error:
                if error and not failure:
                    run.errors += 1
                else:
                    run.failed += 1
                run.failed_tokens.add(f"{classname}.{name}".lower())
            elif skipped:
                run.skipped += 1
            else:
                run.passed += 1


def load_test_run(reports_dir: Path) -> TestRun:
    """Прочитать pytest+vitest JUnit-отчёты из `reports_dir`. Никогда не падает."""
    run = TestRun()
    if not reports_dir.is_dir():
        return run
    for fname in (_PYTEST_REPORT, _VITEST_REPORT):
        path = reports_dir / fname
        if path.is_file():
            _ingest_junit(path, run)
    return run


def _router_status(router: Router | None, run: TestRun) -> str:
    if router is None:
        return PLAN
    if router.is_stub:
        return WIP
    if run.feature_failed(router.name):
        return FAIL
    return DONE


def _sql_status(name: str, sql_objects: set[str], run: TestRun) -> str:
    if name not in sql_objects:
        return PLAN
    if run.feature_failed(name):
        return FAIL
    return DONE


def _router_line(name: str, routers: dict[str, Router], run: TestRun) -> str:
    router = routers.get(name)
    status = _router_status(router, run)
    if router is None:
        return f"- {PLAN} `{name}` — роутер (план, файла нет)"
    prefix = f" (`{router.prefix}`)" if router.prefix else ""
    if router.is_stub:
        note = " — заглушка 501"
    elif status == FAIL:
        note = " — тесты падают (последний прогон)"
    else:
        note = ""
    return f"- {status} `{name}`{prefix}{note}"


def _sql_line(name: str, sql_objects: set[str], run: TestRun) -> str:
    status = _sql_status(name, sql_objects, run)
    if status == PLAN:
        note = " — план, объекта нет"
    elif status == FAIL:
        note = " — тесты падают (последний прогон)"
    else:
        note = ""
    return f"- {status} `{name}`{note}"


def _test_summary_lines(run: TestRun) -> list[str]:
    """Секция «Тесты (последний прогон)» — счётчики без меток времени."""
    lines = ["## Тесты (последний прогон)", ""]
    if not run.found:
        lines += [
            f"- {WIP} Прогон тестов не найден (`reports/{_PYTEST_REPORT}`, "
            f"`reports/{_VITEST_REPORT}`).",
            "  Статусы посчитаны только по диску. Запусти `bash scripts/check.sh`, "
            "чтобы сверить с тестами.",
            "",
        ]
        return lines
    verdict = f"{DONE} всё зелёное" if run.green else f"{FAIL} есть падения"
    lines += [
        f"- Итог: **{verdict}** — "
        f"{run.passed} passed · {run.failed} failed · {run.errors} errors · "
        f"{run.skipped} skipped (всего {run.total}).",
        f"- Источник: `reports/{_PYTEST_REPORT}` (pytest) + "
        f"`reports/{_VITEST_REPORT}` (vitest), последний прогон.",
        "",
    ]
    return lines


def render(
    routers: dict[str, Router], sql_objects: set[str], run: TestRun | None = None
) -> str:
    """Собирает Markdown-документ из фактов диска + закрепления вех + прогона тестов."""
    run = run or TestRun()
    lines: list[str] = [
        "# CURRENT_STATUS — реализовано vs план",
        "",
        "> ⚠️ **Не редактировать вручную.** Источник — `scripts/gen_status.py` "
        "(00-CONTRACT §8.9).",
        "> Перечень роутеров/таблиц берётся из факта (`api/routers`, `api/sql`), не из README.",
        f"> Статус: {DONE} реализовано (тесты зелёные) · {WIP} заглушка (501)/в работе · "
        f"{FAIL} тесты падают · {PLAN} план (файла нет).",
        "> «✅ требует зелёных тестов»: сверка с последним прогоном pytest/vitest (`reports/`).",
        "",
    ]

    # ── Тесты (последний прогон) ─────────────────────────────────
    lines += _test_summary_lines(run)

    # ── Сводка (детерминированные счётчики) ──────────────────────
    r_done = sum(1 for r in routers.values() if not r.is_stub and not run.feature_failed(r.name))
    r_stub = sum(1 for r in routers.values() if r.is_stub)
    r_fail = sum(1 for r in routers.values() if not r.is_stub and run.feature_failed(r.name))
    sql_fail = sum(1 for n in sql_objects if run.feature_failed(n))
    sql_done = len(sql_objects) - sql_fail
    lines += [
        "## Сводка",
        "",
        f"- Роутеры (`api/routers`): **{len(routers)}** "
        f"({DONE} {r_done} · {WIP} {r_stub} · {FAIL} {r_fail})",
        f"- SQL-объекты (`api/sql`): **{len(sql_objects)}** "
        f"({DONE} {sql_done} · {FAIL} {sql_fail})",
        "",
    ]

    # ── Секции вех ───────────────────────────────────────────────
    for sid, title, members in SECTIONS:
        lines.append(f"## {sid} · {title}")
        lines.append("")
        for name in sorted(members.get("routers", [])):
            lines.append(_router_line(name, routers, run))
        for name in sorted(members.get("sql", [])):
            lines.append(_sql_line(name, sql_objects, run))
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
            lines.append(_router_line(name, routers, run))
        for name in extra_sql:
            lines.append(_sql_line(name, sql_objects, run))
        lines.append("")

    # ── Инвентарь (чистый факт с диска, сорт по id) ──────────────
    lines.append("## Инвентарь (факт с диска)")
    lines.append("")
    lines.append("### Роутеры (`api/routers/*.py`)")
    lines.append("")
    for name in sorted(routers):
        lines.append(_router_line(name, routers, run))
    lines.append("")
    lines.append("### SQL-объекты (`api/sql/*.sql`)")
    lines.append("")
    for name in sorted(sql_objects):
        lines.append(_sql_line(name, sql_objects, run))
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def generate(out_path: Path, reports_dir: Path = _DEFAULT_REPORTS) -> Path:
    """Пишет `CURRENT_STATUS.md`. Возвращает путь."""
    content = render(discover_routers(), discover_sql_objects(), load_test_run(reports_dir))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Генератор CURRENT_STATUS.md из факта (api/routers, api/sql) + прогона тестов."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_DEFAULT_OUT,
        help="путь к выходному файлу (default: CURRENT_STATUS.md в корне)",
    )
    parser.add_argument(
        "-r",
        "--reports-dir",
        type=Path,
        default=_DEFAULT_REPORTS,
        help="каталог JUnit-отчётов pytest/vitest (default: reports/)",
    )
    args = parser.parse_args(argv)
    out = generate(args.output, args.reports_dir)
    rel = out.relative_to(_ROOT) if out.is_relative_to(_ROOT) else out
    print(f"CURRENT_STATUS → {rel} ({out.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
