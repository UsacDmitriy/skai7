# f8 · Заявки (`/tickets`)

> Трек **Frontend**. Против `00-CONTRACT.md` §3.4 (actions) + §7.4 (`GET /api/tickets`) + §7.5 (`Ticket`) + §7.8 (AC «Tickets»).
> **Модель:** 🔵 Sonnet — детерминированная логика/вёрстка против контракта; гейт = секция Check.
> **Владеет:** `web/src/pages/Tickets.tsx`. Использует UI-примитивы d2 (`@/components`) и API-клиент f2.
> Идея #6 «Заявки». Иконки — `lucide-react`.

## Цель

Реестр заявок, порождённых действиями над инцидентами (журнал `output/actions.csv` через бэк).
Один ряд = один `Ticket` (§7.5). Маршрут `/tickets` (f1).

## Экран

Данные: `client.getTickets()` → `Ticket[]` (§7.5: `{id, created_at, incident_id, action, comment, status}`,
`status ∈ {new, in_progress, closed}`). Поля по контракту — схему не дублировать.

- **Таблица** (`DataTable` d2): дата (`created_at`), тип (`action` — `mark_reviewed/create_task/
  export_report/request_archive/call_driver`, §3.4), инцидент (`incident_id`, ссылка → `/incidents/:id`),
  комментарий (`comment`), статус-бейдж (`new`/`in_progress`/`closed`).
- **Статус-бейдж** цветом: `new` (нейтральный/primary), `in_progress` (warning), `closed` (ok). Через
  токены d1, без прямых hex.
- **Фильтры**: по типу (`action`), по статусу (`new/in_progress/closed`), по дате (диапазон/период).
  Фильтрация клиентская по загруженному списку.
- Клик по `incident_id` → `/incidents/:id`.
- Состояния loading/error/empty.

## Зависимости и параллельность

- Зависит от: **f2/x2** — клиент дополнить методом **`getTickets() → Ticket[]`** (`GET /api/tickets`,
  §7.4) и типом **`Ticket`** (§7.5). До готовности — фикстуры f3. **d2** (`DataTable`, бейдж/`Card`).
  Маршрут — f1.
- Параллелится с f5/f6/f7 — отдельный файл, без пересечений по владению.

## Check

- `/tickets` рендерит таблицу на живом API (после `make db` + бэк, `output/actions.csv`) и на фикстурах
  (`VITE_USE_FIXTURES=true`).
- Колонки соответствуют `Ticket` (§7.5); `action` отображается человекочитаемо.
- Статус-бейдж окрашен: new/in_progress/closed (токены d1).
- Фильтры по типу, статусу и дате корректно сужают список.
- Клик по `incident_id` открывает `/incidents/:id`.
- **Оверлей «⏱ Просрочено»** рисуется по `is_overdue=true` (§7.5), а **не** по `status` — у `closed`
  оверлея нет; `deadline=null` → `is_overdue=false` → без оверлея.
- **Empty-state**: пустой список (нет `output/actions.csv` или `[]`) → дружелюбная плашка «Заявок пока
  нет», а не ошибка; фильтр без совпадений → отдельный текст «Ничего не найдено» + сброс фильтров.
- **error-state**: сбой `getTickets()` → плашка с кнопкой «Повторить»; **loading**: скелетон/спиннер
  таблицы (без layout-shift).
- **a11y таблицы**: `<table>` с `<th scope="col">`, сортировка через `aria-sort`, кнопки сортировки
  доступны с клавиатуры; ссылка `incident_id` фокусируема; бейдж статуса дублирует цвет текстом.
- **Локаль дат**: `created_at`/`deadline` форматируются через общий util локали/таймзоны (не сырой ISO,
  не `Date.now()` в рендере).

## Состояния и edge-cases

- **loading** → скелетон таблицы; **empty** (нет CSV / `[]`) → «Заявок пока нет» (не ошибка, §7.8/Edge #6);
  **empty по фильтру** → «Ничего не найдено» + сброс; **error** → плашка + «Повторить».
- `is_overdue` — единственный источник оверлея «⏱ Просрочено»; не путать со `status` (enum §3.1).
- Сортировка по дате/статусу стабильна и отражена в `aria-sort`.
- Проверка на живом API и фикстурах (`VITE_USE_FIXTURES=true`); `npm run typecheck` зелёный.
