# t6 · Remote CI + nightly live-smoke (по research-отчёту)

> Трек **Tests/CI** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.9. **Владеет:** `.github/workflows/ci.yml`,
> `.github/workflows/nightly-smoke.yml`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — пайплайн против существующих make/скриптов; гейт = зелёный CI.
> **Волна 4.3** (AI Ops & Trust), окно 3. Поднимает локальный `scripts/check.sh` в remote и страхует от fixture-маскировки.
> **Каталог `.github/workflows/` + скелет `ci.yml` создаются в prep `w3-19`** (этот промпт доводит CI + nightly live-smoke).

## Цель

Закрепить качество в **remote CI** (а не только локальный gate) и поймать backend-регресс, который
скрывает fixture mode: отдельный **nightly smoke на ЖИВОМ API** (без `VITE_USE_FIXTURES`).

## Состав

- `.github/workflows/ci.yml` — на PR/push: `make install` → `make db` → `make lint` → `make typecheck`
  → `make test` (зеркало `scripts/check.sh`). Кэш зависимостей.
- `.github/workflows/nightly-smoke.yml` — по расписанию: поднять `make api`, прогнать сквозной smoke на
  **живом** API (incidents/reports/forecast/zones/copilot), `VITE_USE_FIXTURES=false`; падение → алерт.

## Check

- CI-workflow проходит на чистом checkout (зелёный lint/typecheck/test).
- Nightly-smoke реально бьёт живой API (не фикстуры) и краснеет при backend-регрессе.
- Пайплайн зеркалит `scripts/check.sh` (нет расхождения локального и remote гейта).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add .github/workflows/ci.yml .github/workflows/nightly-smoke.yml
git commit -m "t6: <что сделано>"
```
