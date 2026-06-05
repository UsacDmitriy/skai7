# Волна 1 · P0 core

Базовый рабочий продукт (идеи #1/#3). Окна 1 (backend) и 2 (web) — параллельно.
Истина по данным/API — [`../00-CONTRACT.md`](../00-CONTRACT.md). Схема и порядок — [`../EXECUTION.md`](../EXECUTION.md).

| Трек (папка) | Окно / ветка | Промпты (порядок) | Проверка |
|---|---|---|---|
| `track-b-backend/` | 1 · `feat/backend` | `b1` → (`b2` ∥ `b4`) + `b3` → `b5` → `b6` | `make db` (54 аларма / 14 типов + `v_incidents`), `make api`, `GET /api/incidents` |
| `track-d-design/` | 2 · `feat/web` | `d1` → `d2` → `d3` | — |
| `track-f-frontend/` | 2 · `feat/web` | `f1` → `f2` → `f3` → `f4` | `VITE_USE_FIXTURES=true npm run dev`, `npm run typecheck` |

Дальше → **Барьер 1** (`../barrier-1-p0/`).
