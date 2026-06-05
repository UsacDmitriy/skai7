# f1 · Vite + React + Tailwind — каркас приложения

> Трек **Frontend**. Против `00-CONTRACT.md` §4/§5. **Владеет:**
> **Модель:** 🟢 Qwen 3.7 max — механическая транскрипция против точной спеки; гейт ловит ошибку.
> `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/index.html`, `web/src/main.tsx`, `web/src/App.tsx`, роутинг.
> Tailwind-конфиг и tokens.css — у d1 (не редактировать, только импортировать). Параллельно со всеми.

## Цель

Рабочий каркас SPA: Vite + React + TS + Tailwind + react-router, общий layout (сайдбар + header из
DESIGN.md), пустые роуты под экраны f4. Прокси к FastAPI добавит x2 (здесь — заглушка комментом).

## Задачи

1. `web/package.json` — зависимости: `react`, `react-dom`, `react-router-dom`, `lucide-react`,
   `recharts`, `clsx`; dev: `vite`, `@vitejs/plugin-react`, `typescript`, `tailwindcss`, `postcss`,
   `autoprefixer`, `@fontsource/inter` (или Google Fonts). Скрипты: `dev`, `build`, `preview`, `typecheck`.
2. `web/vite.config.ts` — plugin-react, alias `@ → src`. (Proxy `/api` оставить TODO для x2.)
3. `web/tsconfig.json` — strict, `paths {"@/*":["src/*"]}`.
4. `web/index.html` + `web/src/main.tsx` — импорт `styles/tokens.css` (d1) и Tailwind, монтаж App.
5. `web/src/App.tsx` — `BrowserRouter`, общий **AppShell** (сайдбар 48/240px + header 56px по DESIGN.md §Components), `Routes`:
   - `/` → редирект на `/monitor`
   - `/monitor` → `Monitor` (f4)
   - `/incidents/:id` → `IncidentCard` (f4)
   - `/report` → `Report` (f4)
   - `/_styleguide` → `_StyleGuide` (d3, ленивый импорт если файл есть)
   - На время отсутствия экранов — плейсхолдер-компонент.
6. AppShell — пункты меню из DESIGN.md (Мониторинг/Видеоаналитика/Дашборды/Парк), иконки Lucide.

## Check

- `npm install && npm run dev` поднимает Vite, страница открывается без ошибок консоли.
- `npm run typecheck` проходит.
- Роуты резолвятся (плейсхолдеры видны), сайдбар/хедер соответствуют DESIGN.md.
