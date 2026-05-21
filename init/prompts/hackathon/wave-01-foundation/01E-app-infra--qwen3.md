# 01E · App.tsx + package.json + Vite + Tailwind
> 💰 **Бюджет:** читать max 1–3 файла · не читать `./data`, `.venv`, `node_modules` · логи: 20–50 строк
> ⚠️ **Один промпт = одна сессия. Не запускать параллельно.**
# Модель: qwen/qwen3-coder:free · $0 · Волна 1
> ✅ Передать: только этот промпт (данные внутри)
> ❌ НЕ читать: AGENTS.md, hackathon/context/DESIGN.md, node_modules

## Файлы (все пути от корня репо)

```
code/frontend/package.json
code/frontend/vite.config.ts
code/frontend/tailwind.config.ts
code/frontend/src/main.tsx
code/frontend/src/index.css
code/frontend/src/App.tsx
```

---

## package.json

```json
{
  "name": "skai-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2",
    "recharts": "^2.12.7",
    "leaflet": "^1.9.4",
    "react-leaflet": "^4.2.1",
    "lucide-react": "^0.441.0"
  },
  "devDependencies": {
    "@types/leaflet": "^1.9.12",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.12",
    "typescript": "~5.5.3",
    "vite": "^5.4.8"
  }
}
```

---

## tailwind.config.ts

```ts
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'skai-primary':  '#1E3A8A',
        'skai-bg':       '#F8FAFC',
        'skai-text':     '#0F172A',
        'skai-muted':    '#64748B',
        'skai-border':   '#E2E8F0',
        'skai-critical': '#DC2626',
        'skai-warning':  '#EA580C',
        'skai-ok':       '#16A34A',
        'skai-dark':     '#0F172A',
        'skai-surface':  '#1E293B',
      },
    },
  },
  plugins: [],
}
```

---

## main.tsx

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
```

---

## App.tsx — каркас с react-router-dom, все 5 маршрутов

```tsx
import { Routes, Route, NavLink } from 'react-router-dom'

// Заглушки — будут заменены промптами волны 03
const EventFeedScreen       = () => <div className="p-8 text-skai-muted">Лента событий (wave-03A)</div>
const LiveMonitorScreen     = () => <div className="p-8 text-skai-muted">Живой мониторинг (wave-03E)</div>
const UnifiedIncidentWindow = () => <div className="p-8 text-skai-muted">Карточка инцидента (wave-03B)</div>
const AnalyticsScreen       = () => <div className="p-8 text-skai-muted">Интерактивный отчёт (wave-03D)</div>
const TicketsScreen         = () => <div className="p-8 text-skai-muted">Заявки (wave-05B)</div>

const NAV = [
  { to: '/',          icon: '⚡', label: 'События' },
  { to: '/monitor',   icon: '🗺', label: 'Мониторинг' },
  { to: '/analytics', icon: '📊', label: 'Аналитика' },
  { to: '/tickets',   icon: '📋', label: 'Заявки' },
]

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-skai-bg">
      <nav className="w-14 hover:w-52 transition-all duration-200 bg-skai-primary
                      flex flex-col pt-4 gap-1 overflow-hidden group flex-shrink-0">
        <div className="px-3 mb-4 font-bold text-white text-lg whitespace-nowrap">SKAI</div>
        {NAV.map(({ to, icon, label }) => (
          <NavLink key={to} to={to} end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 mx-1 rounded-lg text-sm font-medium
               whitespace-nowrap transition-colors ${
                 isActive
                   ? 'bg-white/20 text-white'
                   : 'text-white/70 hover:bg-white/10 hover:text-white'
               }`
            }
          >
            <span className="flex-shrink-0">{icon}</span>
            <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-150">{label}</span>
          </NavLink>
        ))}
      </nav>
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/"             element={<EventFeedScreen />} />
          <Route path="/monitor"      element={<LiveMonitorScreen />} />
          <Route path="/incident/:id" element={<UnifiedIncidentWindow />} />
          <Route path="/analytics"    element={<AnalyticsScreen />} />
          <Route path="/tickets"      element={<TicketsScreen />} />
        </Routes>
      </main>
    </div>
  )
}
```

---

## Acceptance criteria

- `npm install && npm run dev` → :5173 открылся без ошибок
- Сайдбар виден, 4 пункта меню
- Все 5 маршрутов работают: `/`, `/monitor`, `/incident/inc-001`, `/analytics`, `/tickets`
- `npm run build` → нет TypeScript ошибок
