import { type ComponentType, lazy, Suspense } from 'react'
import {
  BarChart2,
  Bell,
  CheckCircle,
  Download,
  FileText,
  Film,
  Heart,
  type LucideIcon,
  Map as MapIcon,
  Radio,
  Shield,
  Zap,
} from 'lucide-react'
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
} from 'react-router-dom'
import { cn } from '@/components/ui/cn'

/**
 * Каркас SPA (f1): BrowserRouter + AppShell (сайдбар 48/240 + header 56) + роуты.
 * Экраны f4 (Monitor/IncidentCard/Report) подключены ленивым импортом.
 * Витрина d3 (`_StyleGuide`) подключается ленивым импортом.
 */

// ── Навигация (источник — DESIGN.md §Components/Боковое меню) ──────────────────
type NavItem = { to: string; label: string; icon: LucideIcon; badge?: string }
type NavGroup = { title: string; items: NavItem[] }

const NAV: NavGroup[] = [
  {
    title: 'Мониторинг',
    items: [
      { to: '/monitor', label: 'Карта', icon: MapIcon },
      { to: '/safety', label: 'Мониторинг безопасности', icon: Shield },
    ],
  },
  {
    title: 'Видеоаналитика',
    items: [
      { to: '/events', label: 'События', icon: FileText },
      { to: '/live', label: 'Прямая трансляция', icon: Radio },
      { to: '/archive', label: 'Видеоархив', icon: Film },
      { to: '/downloads', label: 'Загрузки', icon: Download },
      { to: '/validation', label: 'Блок валидации', icon: CheckCircle },
      { to: '/response', label: 'Блок реагирования', icon: Bell },
    ],
  },
  {
    title: 'Дашборды и отчёты',
    items: [
      { to: '/dashboards', label: 'Дашборды', icon: BarChart2 },
      { to: '/report', label: 'Отчёты', icon: FileText },
      { to: '/quick-report', label: 'Быстрый отчёт', icon: Zap, badge: 'NEW' },
    ],
  },
  {
    title: 'Парк',
    items: [{ to: '/fleet-health', label: 'Здоровье парка', icon: Heart }],
  },
]

// ── Сайдбар: 48px свёрнут, разворачивается до 240px по hover ───────────────────
function Sidebar() {
  return (
    <aside className="group/sb sticky top-0 z-20 flex h-screen w-12 shrink-0 flex-col overflow-hidden border-r border-border bg-surface transition-[width] duration-200 ease-out hover:w-60">
      <div className="flex h-14 items-center gap-2 px-3">
        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-primary text-[13px] font-bold text-white">
          S
        </div>
        <span className="whitespace-nowrap text-[15px] font-bold tracking-tight text-ink opacity-0 transition-opacity duration-200 group-hover/sb:opacity-100">
          SKAI
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto py-2">
        {NAV.map((group) => (
          <div key={group.title} className="flex flex-col gap-0.5">
            <div className="h-4 px-3 text-[11px] font-medium uppercase tracking-wider text-muted opacity-0 transition-opacity duration-200 group-hover/sb:opacity-100">
              {group.title}
            </div>
            {group.items.map((item) => (
              <SidebarLink key={item.to} item={item} />
            ))}
          </div>
        ))}
      </nav>
    </aside>
  )
}

function SidebarLink({ item }: { item: NavItem }) {
  const { to, label, icon: Icon, badge } = item
  return (
    <NavLink
      to={to}
      title={label}
      className={({ isActive }) =>
        cn(
          'relative flex h-9 items-center gap-3 px-3 text-[13px] transition-colors',
          'border-l-[3px] border-transparent',
          isActive
            ? 'border-l-primary bg-primary-50 font-medium text-primary'
            : 'text-muted hover:bg-bg hover:text-ink',
        )
      }
    >
      <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
      <span className="flex-1 whitespace-nowrap opacity-0 transition-opacity duration-200 group-hover/sb:opacity-100">
        {label}
      </span>
      {badge ? (
        <span className="rounded bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-white opacity-0 transition-opacity duration-200 group-hover/sb:opacity-100">
          {badge}
        </span>
      ) : null}
    </NavLink>
  )
}

// ── Header 56px ───────────────────────────────────────────────────────────────
function Header() {
  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-4 border-b border-border bg-surface px-5 shadow-[0_1px_3px_rgba(0,0,0,0.08)]">
      <div className="text-[15px] font-bold tracking-tight text-ink">
        SKAI Online
      </div>
      <div className="text-[13px] text-muted">Мониторинг безопасности</div>
      <div className="ml-auto flex items-center gap-3 text-[13px] tabular-nums text-muted">
        {/* TODO (f4/f5): живые счётчики инцидентов из API */}
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-ok" />
          Онлайн
        </span>
      </div>
    </header>
  )
}

function AppShell() {
  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

// ── Плейсхолдер для ещё не реализованных экранов (f4+) ─────────────────────────
function Placeholder({ title }: { title: string }) {
  return (
    <div className="grid h-full place-items-center">
      <div className="text-center">
        <div className="text-[18px] font-semibold text-ink">{title}</div>
        <div className="mt-1 text-[13px] text-muted">Экран в разработке</div>
      </div>
    </div>
  )
}

// ── Ленивые экраны f4 + витрина d3 ────────────────────────────────────────────
const Monitor = lazy(() => import('@/pages/Monitor')) as ComponentType
const IncidentCard = lazy(() => import('@/pages/IncidentCard')) as ComponentType
const Report = lazy(() => import('@/pages/Report')) as ComponentType
const StyleGuide = lazy(() => import('@/pages/_StyleGuide')) as ComponentType

export default function App() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/monitor" replace />} />
          <Route
            path="/monitor"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <Monitor />
              </Suspense>
            }
          />
          <Route
            path="/incidents/:id"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <IncidentCard />
              </Suspense>
            }
          />
          <Route
            path="/report"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <Report />
              </Suspense>
            }
          />
          <Route
            path="/_styleguide"
            element={
              <Suspense fallback={<Placeholder title="Загрузка витрины…" />}>
                <StyleGuide />
              </Suspense>
            }
          />
          {/* Будущие экраны из меню DESIGN.md — пока единый плейсхолдер. */}
          <Route path="*" element={<Placeholder title="Раздел в разработке" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
