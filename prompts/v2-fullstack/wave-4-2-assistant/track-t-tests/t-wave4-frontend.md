# t-wave4-frontend · Vitest по AI-компонентам (Волна 4)

> Трек **Tests** (`feat/tests`, окно 3). Против `00-CONTRACT.md` §8.4.
> **Модель:** 🔵 Sonnet — тест-авторство против контракта; гейт = vitest.
> **Владеет:** `web/**/ai/*.test.tsx`. Гонится после d7/f15–f19. Баги эскалируются треку F, не правятся.

## Цель

Покрыть рендер/взаимодействие AI-компонентов фронта (RTL + vitest), happy + негатив.

## Состав

- `SceneContextChip`: рендерит погоду/день-ночь по props; `unknown` → нейтральный вид.
- `DiscrepancyBadge`: показывается только при `discrepancy=true`.
- `ForecastSparkline`: рисует коридор `ci_low/ci_high` и точку аномалии; пустой trend → empty.
- `RiskHeatLayer`: принимает `RiskZone[]` и тоггл `kind` (мок Leaflet).
- `Copilot`: ввод→ответ на фикстурах; пустой ввод заблокирован; ошибка→retry.
- `SabotageWidget`: показывает `verdict_confidence`/`verdict_reason`; без полей → прежний вид.

## Check

- `npm run test` (vitest) зелёный; покрытие AI-компонентов в гейт `w3-4` (Волна 3 — общий гейт `web/src`≥80%).
- Тесты детерминированы, без сети (фикстуры/моки).

## Коммит (обязательно)

Заверши промпт коммитом в свою ветку — **merge на барьере берёт только коммиты**:

```bash
# параллельно в одном worktree — стейджи только свои файлы (НЕ git add -A)
git add web/src/components/ai
git commit -m "t-wave4-frontend: <что сделано>"
```
