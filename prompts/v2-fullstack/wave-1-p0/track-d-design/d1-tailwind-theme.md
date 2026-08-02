# d1 · Tailwind-тема и дизайн-токены

> Трек **Design**. Кодит против `00-CONTRACT.md` §4 и `init/context/DESIGN.md`.
> **Исполнение:** bounded ClinePass package; role `worker`; route category `code`; exact route/model only from `tools/clinepass-mcp/models.env` — механическая транскрипция против точной спеки; гейт ловит ошибку.
> **Владеет файлами:** `web/tailwind.config.ts`, `web/src/styles/tokens.css`. Только они.
> Параллельно с d2/d3 и со всеми треками B/F.

## Цель

Перенести дизайн-систему SKAI (`init/context/DESIGN.md`) в Tailwind-конфиг и CSS-переменные, чтобы d2/f4 строили компоненты на токенах, а не на хардкоде.

## Задачи

1. `web/tailwind.config.ts`:
   - `theme.extend.colors`: `primary` (#1E3A8A), `primary-dark` (#1E3070), `primary-50` (#EFF6FF), `bg` (#F8FAFC), `surface` (#FFFFFF), `ink` (#0F172A), `muted` (#64748B), `border` (#E2E8F0).
   - Severity-палитра как вложенные объекты: `critical {DEFAULT:#DC2626, bg:#FEE2E2, text:#991B1B}`, `high {#EA580C/#FEF3C7/#B45309}`, `warning {#EAB308/#FEF9C3/#854D0E}`, `ok {#16A34A/#DCFCE7/#166534}`.
   - `fontFamily.sans = ['Inter', ...system]`; `borderRadius`: `md:6px`, `xl:12px`; `spacing` на базе 4px (наследуется).
   - Контент-пути: `./index.html`, `./src/**/*.{ts,tsx}`.
2. `web/src/styles/tokens.css`:
   - `:root` CSS-переменные дублируют палитру (`--sev-critical`, `--sev-critical-bg`, …) для использования вне Tailwind (например, инлайн-градиент score-bar).
   - Класс/утилита `.score-bar-fill { background: linear-gradient(90deg,#16A34A 0%,#EAB308 50%,#DC2626 100%); }`.
   - Импорт шрифта Inter (Google Fonts или `@fontsource/inter` — указать вариант).
   - `tabular-nums` утилита для чисел.

## Маппинг severity (зафиксировать в комментарии конфига)

API `severity ∈ {critical, high, medium, low}` → токены: `critical→critical`, `high→high`,
**`medium→warning`** (жёлтый), **`low→ok`** (зелёный). Эта таблица — единственно верная для всего фронта.

## Check

- `web/tailwind.config.ts` импортируется без ошибок типов.
- Классы `bg-primary`, `text-critical-text`, `bg-warning-bg` разрешаются.
- `tokens.css` содержит все 4 severity и `.score-bar-fill`.
