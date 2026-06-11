import { type ComponentType, lazy, Suspense } from 'react'
import {
  BarChart2,
  Bell,
  Bot,
  CheckCircle,
  ClipboardList,
  Download,
  FileText,
  Film,
  Gauge,
  Heart,
  type LucideIcon,
  Map as MapIcon,
  Navigation,
  Radio,
  Shield,
  Zap,
} from 'lucide-react'
import {
  BrowserRouter,
  type Location,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import { ComingSoon, type ComingSoonProps } from '@/components/ComingSoon'
import { cn } from '@/components/ui/cn'
import { navForRole, type Role, RoleProvider, useRole } from '@/state/role'

/**
 * Каркас SPA (f1): BrowserRouter + AppShell (сайдбар 48/240 + header 56) + роуты.
 * Экраны f4 (Monitor/IncidentCard/Report) подключены ленивым импортом.
 * Витрина d3 (`_StyleGuide`) подключается ленивым импортом.
 * Роль оператора (f13) — общий `RoleProvider` над всем деревом: лента и карта
 * читают одну роль согласованно, значение персистится в localStorage.
 */

// ── Навигация (источник — DESIGN.md §Components/Боковое меню) ──────────────────
// f24 · Опциональное поле `roles` (пункт/группа) — роль-видимость, согласованная
// с контент-фильтром (`roleFilter.ts`): нет `roles` ⇒ видно всем (безопасный
// дефолт). Сейчас не проставлено нигде (контракт мандатит фильтрацию данных, а не
// разделов меню) — механизм заведён, фактическая видимость для всех ролей едина.
type NavItem = {
  to: string
  label: string
  icon: LucideIcon
  badge?: string
  roles?: Role[]
}
type NavGroup = { title: string; items: NavItem[]; roles?: Role[] }

// f22 · Таксономия бейджей навигации (честность пунктов меню):
//   • живой экран (или редирект на живой)      → без бейджа;
//   • scaffold / in-progress (экран на подходе) → `Скоро` (снимут f17/f21);
//   • вне скоупа / нужен новый источник данных  → `Будущее` (волна не обещана).
// Прежний `W4` упразднён: 6 из 8 «W4»-пунктов не имели владельца — 3 дубля ушли
// в редирект на живые экраны Волны 4, остальные размечены `Скоро`/`Будущее`.
const NAV: NavGroup[] = [
  {
    title: 'Мониторинг',
    items: [
      { to: '/monitor', label: 'Карта', icon: MapIcon },
      // /safety → редирект на /metrics (живой экран): бейдж снят.
      { to: '/safety', label: 'Мониторинг безопасности', icon: Shield },
    ],
  },
  {
    title: 'Видеоаналитика',
    items: [
      { to: '/events', label: 'События', icon: FileText },
      { to: '/live', label: 'Прямая трансляция', icon: Radio, badge: 'Будущее' },
      { to: '/archive', label: 'Видеоархив', icon: Film, badge: 'Будущее' },
      { to: '/downloads', label: 'Загрузки', icon: Download, badge: 'Будущее' },
      { to: '/validation', label: 'Блок валидации', icon: CheckCircle, badge: 'Будущее' },
      { to: '/response', label: 'Блок реагирования', icon: Bell, badge: 'Будущее' },
      { to: '/tickets', label: 'Заявки', icon: ClipboardList },
    ],
  },
  {
    title: 'Дашборды и отчёты',
    items: [
      // /dashboards → редирект на /metrics (живой экран): бейдж снят.
      { to: '/dashboards', label: 'Дашборды', icon: BarChart2 },
      { to: '/report', label: 'Отчёты', icon: FileText },
      // /quick-report → редирект на /copilot (живой экран): бейдж снят.
      { to: '/quick-report', label: 'Быстрый отчёт', icon: Zap },
    ],
  },
  {
    title: 'Парк',
    items: [
      { to: '/fleet-health', label: 'Здоровье парка', icon: Heart },
      { to: '/navigation', label: 'Навигация (РЭБ)', icon: Navigation },
    ],
  },
  {
    // Каркас под Волну 4: /copilot (§8.3) и /metrics (§8.7) рендерят scaffold-
    // страницы. Бейдж `Скоро` снимут промпты f17/f21, когда экраны будут влиты.
    title: 'AI',
    items: [
      { to: '/copilot', label: 'Копилот', icon: Bot, badge: 'Скоро' },
      { to: '/metrics', label: 'Метрики', icon: Gauge, badge: 'Скоро' },
    ],
  },
]

// ── Сайдбар: 48px свёрнут, разворачивается до 240px по hover ───────────────────
function Sidebar() {
  // f24 · Меню согласовано с ролью (единый источник — RoleProvider/useRole).
  // Дефолт = все секции (ни один пункт не помечен `roles`), но NAV теперь умеет
  // роль-фильтрацию, согласованную с in-screen контент-фильтром (issue #4).
  const { role } = useRole()
  const groups = navForRole(role, NAV)
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
        {groups.map((group) => (
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
        <span className="rounded border border-border bg-bg px-1.5 py-0.5 text-[10px] font-semibold text-muted opacity-0 transition-opacity duration-200 group-hover/sb:opacity-100">
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

// ── Суспенс-фолбэк «Загрузка…» (единственное назначение Placeholder) ───────────
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

// ── Сигнпостинг «мёртвых» пунктов меню (w3-13, §9.4) ──────────────────────────
// Карта `path → ComingSoon`: честная подпись «скоро / Волна 4» вместо пустого 404.
// Разделы Волны 4 (видеостриминг, workflow, BI-копилот) ещё не реализованы.
// f22 · /safety, /dashboards, /quick-report ушли из карты — теперь это редиректы
// на живые экраны Волны 4 (см. <Navigate> в AppRoutes), а не сигнпост-заглушки.
// Видеостриминг и workflow — `kind: 'future'`: волна не обещана, нужен новый источник.
const COMING_SOON: Record<string, ComingSoonProps> = {
  '/live': {
    title: 'Прямая трансляция',
    description:
      'Нужен live-источник: датасет исторический (94 MP4 по событию), потока с бортовых камер нет.',
    wave: 4,
    kind: 'future',
  },
  '/archive': {
    title: 'Видеоархив',
    description:
      'Нужен live-источник (датасет исторический). Покадровое видео по событию уже доступно в карточке инцидента — «Запросить архив».',
    wave: 4,
    kind: 'future',
  },
  '/downloads': {
    title: 'Загрузки',
    description:
      'Массовая выгрузка фрагментов — нужен live-источник (датасет исторический).',
    wave: 4,
    kind: 'future',
  },
  '/validation': {
    title: 'Блок валидации',
    description: 'Очередь валидации алармов — workflow-движок, будущая волна.',
    wave: 4,
    kind: 'future',
  },
  '/response': {
    title: 'Блок реагирования',
    description:
      'Маршрутизация и эскалация реагирования — workflow-движок, будущая волна.',
    wave: 4,
    kind: 'future',
  },
}

// Catch-all: по текущему пути берём карточку из карты, иначе — общий «скоро».
function ComingSoonRoute() {
  const { pathname } = useLocation()
  const meta = COMING_SOON[pathname] ?? {
    title: 'Раздел в разработке',
    description: 'Этот экран появится в одной из следующих волн.',
    wave: 4,
  }
  return <ComingSoon {...meta} />
}

// ── Ленивые экраны f4 + витрина d3 ────────────────────────────────────────────
const EventsFeed = lazy(() => import('@/pages/EventsFeed')) as ComponentType
const Monitor = lazy(() => import('@/pages/Monitor')) as ComponentType
const IncidentCard = lazy(() => import('@/pages/IncidentCard')) as ComponentType
const Report = lazy(() => import('@/pages/Report')) as ComponentType
const Tickets = lazy(() => import('@/pages/Tickets')) as ComponentType
const TripDossier = lazy(() => import('@/pages/TripDossier')) as ComponentType
const RebRecovery = lazy(() => import('@/pages/RebRecovery')) as ComponentType
const FleetHealth = lazy(() => import('@/pages/FleetHealth')) as ComponentType
const FuelCard = lazy(() => import('@/pages/FuelCard')) as ComponentType
const SensorCard = lazy(() => import('@/pages/SensorCard')) as ComponentType
const NavProblemList = lazy(
  () => import('@/pages/NavProblemList'),
) as ComponentType
// Каркас Волны 4 (w3-18): сейчас таргеты рендерят ComingSoon; f17/f21 заменят
// содержимое страниц без правок роутинга (точка расширения готова).
const Copilot = lazy(() => import('@/pages/Copilot')) as ComponentType
const Metrics = lazy(() => import('@/pages/Metrics')) as ComponentType
const StyleGuide = lazy(() => import('@/pages/_StyleGuide')) as ComponentType
const DispatchAlert = lazy(() => import('@/pages/DispatchAlert')) as ComponentType

/**
 * Роуты приложения. Маршрут `/alert/:id` (f9) — overlay-модал: рендерится
 * поверх фонового экрана (background-location pattern). При навигации с
 * `state.backgroundLocation` основной `<Routes>` продолжает показывать фон
 * (он не размонтируется), а модал рисуется вторым `<Routes>` сверху.
 */
function AppRoutes() {
  const location = useLocation()
  const state = location.state as { backgroundLocation?: Location } | null
  const background = state?.backgroundLocation

  return (
    <>
      <Routes location={background ?? location}>
        <Route element={<AppShell />}>
          <Route
            index
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <EventsFeed />
              </Suspense>
            }
          />
          <Route
            path="/events"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <EventsFeed />
              </Suspense>
            }
          />
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
            path="/tickets"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <Tickets />
              </Suspense>
            }
          />
          <Route
            path="/trip/:id"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <TripDossier />
              </Suspense>
            }
          />
          <Route
            path="/reb/:id"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <RebRecovery />
              </Suspense>
            }
          />
          <Route
            path="/fleet-health"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <FleetHealth />
              </Suspense>
            }
          />
          <Route
            path="/fleet-health/fuel/:plate"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <FuelCard />
              </Suspense>
            }
          />
          <Route
            path="/fleet-health/sensors/:plate"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <SensorCard />
              </Suspense>
            }
          />
          <Route
            path="/navigation"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <NavProblemList />
              </Suspense>
            }
          />
          {/* f22 redirect (ASSUMPTION, см. промпт f22): дубли реальных экранов
              Волны 4 ведут на живой экран по сходству. §7.8/§8 их НЕ мандатируют —
              откат: появился промпт-владелец экрана → снять Navigate, вернуть
              ключ в COMING_SOON (ревизия на каждом барьере x9+). */}
          <Route path="/safety" element={<Navigate to="/metrics" replace />} />
          <Route
            path="/dashboards"
            element={<Navigate to="/metrics" replace />}
          />
          <Route
            path="/quick-report"
            element={<Navigate to="/copilot" replace />}
          />
          {/* Каркас Волны 4 (w3-18): /copilot (f17) и /metrics (f21). До влития —
              ComingSoon; f17/f21 заменят страницы без правок этих маршрутов. */}
          <Route
            path="/copilot"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <Copilot />
              </Suspense>
            }
          />
          <Route
            path="/metrics"
            element={
              <Suspense fallback={<Placeholder title="Загрузка…" />}>
                <Metrics />
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
          {/* Экраны Волны 4 из меню — честный ComingSoon вместо пустого 404. */}
          <Route path="*" element={<ComingSoonRoute />} />
        </Route>
      </Routes>

      {/* Overlay-маршрут f9: модал поверх фона (фон выше не размонтируется). */}
      <Routes>
        <Route
          path="/alert/:id"
          element={
            <Suspense fallback={null}>
              <DispatchAlert />
            </Suspense>
          }
        />
        <Route path="*" element={null} />
      </Routes>
    </>
  )
}

export default function App() {
  return (
    <RoleProvider>
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <AppRoutes />
      </BrowserRouter>
    </RoleProvider>
  )
}
