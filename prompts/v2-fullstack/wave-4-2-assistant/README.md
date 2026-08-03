# Волна 4.2 · Ассистент + визуализация (AI-слой)

Вторая под-волна Волны 4 (после барьера 4.1). Backend-копилот и фронт идут **параллельно** (окна 1 и 2),
тесты — окно 3. Кодим против `00-CONTRACT.md` **§8**. LLM-ветки — Groq + детерминированный фолбэк (как nlu).

| Окно | Промпты | Исполнение |
|---|---|---|
| 1 Backend | `b21` copilot (tool-use, RU/EN) ∥ `b22` narrative-reports ∥ `b23` sabotage-verdict | b21: owner-only · Claude/Codex; b22/b23: bounded ClinePass · worker · `code` |
| 2 Web | `f15` scene-card → `f16` forecast-report ; `f17` copilot-ui ∥ `f18` risk-heatmap ∥ `f19` sabotage-verdict | f17/f18: owner-only · Claude/Codex; f15/f16/f19: bounded ClinePass · worker · `code` |
| 3 Tests | `per-feature/tu-copilot` (фолбэк) ∥ `t-wave4-frontend` (vitest AI-компоненты) | bounded ClinePass · worker · `code` |

Дальше → **Барьер 4.2** (`../barrier-4-2-assistant/x7-e2e-wave4.md`) — e2e ассистента + регресс 4.1.
Слой измеримости/безопасности/explainability вынесен в **Волну 4.3** (`../wave-4-3-ops-trust/`); `main`
продвигает её барьер **x8** (`../barrier-4-3-ops-trust/x8-ops-trust.md`).

> Каждый промпт заканчивается секцией `## Коммит`.
>
> ⚠️ **Параллельный коммит без `git add -A`.** `b21∥b22∥b23` и `f17∥f18∥f19` идут одновременно в одной
> ветке — `## Коммит` каждого стейджит **только свои файлы** (файлы дизъюнктны, конфликта содержимого нет).
> Роутер `b21` (`copilot`) **автодискаверится** (`api/main.py:_discover_routers`) — общий
> `api/routers/__init__.py` (`ALL_ROUTERS`, легаси) не трогаем; `b23` — аддитивная правка sabotage (без роутера).
