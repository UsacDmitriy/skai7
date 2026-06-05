# Волна 4.2 · Ассистент + визуализация (AI-слой)

Вторая под-волна Волны 4 (после барьера 4.1). Backend-копилот и фронт идут **параллельно** (окна 1 и 2),
тесты — окно 3. Кодим против `00-CONTRACT.md` **§8**. LLM-ветки — Groq + детерминированный фолбэк (как nlu).

| Окно | Промпты | Модель |
|---|---|---|
| 1 Backend | `b21` copilot (tool-use, RU/EN) ∥ `b22` narrative-reports ∥ `b23` sabotage-verdict | b21 🔴 · b22/b23 🔵 |
| 2 Web | `f15` scene-card → `f16` forecast-report ; `f17` copilot-ui ∥ `f18` risk-heatmap ∥ `f19` sabotage-verdict | f17/f18 🔴 · f15/f16/f19 🔵 |
| 3 Tests | `per-feature/tu-copilot` (фолбэк) ∥ `t-wave4-frontend` (vitest AI-компоненты) | 🔵 Sonnet |

Дальше → **Барьер 4.2** (`../barrier-4-2-assistant/x7-e2e-wave4.md`) → продвигает `main`.

> Каждый промпт заканчивается секцией `## Коммит`. ⚠ `b20`/`b21`/`b23` регистрируют свои роутеры в `ALL_ROUTERS`.
