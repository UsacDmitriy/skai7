# Волна 2.2 · Прикладные экраны (P1/P2)

Заявки, диспетч-алерт, видеодосье, РЭБ, саботаж, карта/роли (идеи #4–#10). Окна 1 и 2 — параллельно.
Истина — [`../00-CONTRACT.md`](../00-CONTRACT.md) (§7.2–§7.6). Схема — [`../EXECUTION.md`](../EXECUTION.md).

| Трек (папка) | Окно / ветка | Промпты | Проверка |
|---|---|---|---|
| `track-b-backend/` | 1 · `feat/backend` | `b11` ∥ `b12` ∥ `b13` (роутеры подключит x2 авто-обходом) | `/api/sabotage`, `/api/reb/{id}`, `/api/trips/{id}`, `/api/tickets` → 200 |
| `track-d-design/` | 2 · `feat/web` | `d4` (map-primitives) | — |
| `track-f-frontend/` | 2 · `feat/web` | `f5`, `f6`, `f8`–`f13` (все параллельно) | экраны `/tickets`, `/trip/:id`, `/reb/:id`, монитор-карта |

Дальше → **Барьер 2.2** (`../barrier-2-2-applied/x4b-smoke-applied-screens.md`).
