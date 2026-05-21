# Промпт 3 — Frontend

Задача: подготовить фронтенд к работе с API.

Рабочая директория: /Users/dimausac/Yandex.Disk.localized/SKAI/Хакатон/hackaton/frontend

1. Убедись, что Tailwind работает:
   - В `tailwind.config.js` content должен включать `["./index.html", "./src/**/*.{ts,tsx}"]`.
   - В `src/index.css` должны быть `@tailwind base; @tailwind components; @tailwind utilities;`.
   - В `src/App.tsx` добавь тестовую кнопку с классом Tailwind (`className="bg-blue-500 text-white p-4 rounded"`) и проверь визуально.

2. Настрой proxy для API в `vite.config.ts`:
   ```ts
   server: {
     proxy: {
       '/api': 'http://localhost:8000'
     }
   }
   ```

3. Установи `react-router-dom` и создай минимальную структуру:
   - `/` — дашборд (список инцидентов из `GET /api/v1/incidents`)
   - `/incidents/:id` — детальная карточка инцидента
   - `/fleet` — список ТС

4. Создай базовый компонент `src/api.ts` с функциями `fetchIncidents()`, `fetchFleet()` (используй `fetch`).

5. Запусти `npm run dev` и проверь, что:
   - Vite стартует на :5173
   - Тестовый запрос к `/api/v1/health` проходит (должен проксироваться на бэкенд)

Результат: фронтенд запускается, ходит за данными на бэкенд, есть роутинг.
