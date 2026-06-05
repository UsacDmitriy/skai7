# Волна 2.1 · Reports & Voice (P1)

Отчёты по водителю/парку + голос/NLU (идея #2). Окна 1 и 2 — параллельно.
Истина — [`../00-CONTRACT.md`](../00-CONTRACT.md) (§7.1–§7.5). Схема — [`../EXECUTION.md`](../EXECUTION.md).

| Трек (папка) | Окно / ветка | Промпты (порядок) | Проверка |
|---|---|---|---|
| `track-b-backend/` | 1 · `feat/backend` | параллельно `b7`, `b8`, `b9` → затем `b10` (после `b7`+`b9`) | `GET /api/reports/fleet`, `/api/reports/driver/{plate}` → 200 |
| `track-d-design/` | 2 · `feat/web` | `d5` (voice-timeline) | — |
| `track-f-frontend/` | 2 · `feat/web` | `f7` (analytics-voice) | `/report` (🎤) рендерится |

Дальше → **Барьер 2.1** (`../barrier-2-p1p2/x4a-smoke-reports-voice.md`).
