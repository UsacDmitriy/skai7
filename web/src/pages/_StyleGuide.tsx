import { type ReactNode, useState } from 'react'
import { Check, Download, Phone } from 'lucide-react'
import {
  Button,
  Card,
  type Column,
  DataTable,
  ScoreBar,
  type Severity,
  SeverityBadge,
  TelemetryChart,
  type TelemetryPoint,
  VideoPlayer,
} from '@/components'

/**
 * `/_styleguide` — витрина всех UI-примитивов d2 во всех состояниях.
 * Двойная роль: приёмка дизайна (соответствие DESIGN.md) и справочник для f4+.
 * Регистрируется роутером f1 ленивым импортом при наличии файла.
 */

// ── Палитра d1 (источник истины: tokens.css / DESIGN.md §Colors) ──────────────
const BASE_TOKENS: { name: string; cssVar: string; hex: string; onLight?: boolean }[] = [
  { name: 'primary', cssVar: '--color-primary', hex: '#1E3A8A' },
  { name: 'primary-dark', cssVar: '--color-primary-dark', hex: '#1E3070' },
  { name: 'primary-50', cssVar: '--color-primary-50', hex: '#EFF6FF', onLight: true },
  { name: 'bg', cssVar: '--color-bg', hex: '#F8FAFC', onLight: true },
  { name: 'surface', cssVar: '--color-surface', hex: '#FFFFFF', onLight: true },
  { name: 'ink', cssVar: '--color-ink', hex: '#0F172A' },
  { name: 'muted', cssVar: '--color-muted', hex: '#64748B' },
  { name: 'border', cssVar: '--color-border', hex: '#E2E8F0', onLight: true },
]

const SEVERITY_TOKENS: { severity: Severity; label: string; accent: string; bg: string; text: string }[] = [
  { severity: 'critical', label: 'critical', accent: '#DC2626', bg: '#FEE2E2', text: '#991B1B' },
  { severity: 'high', label: 'high', accent: '#EA580C', bg: '#FEF3C7', text: '#B45309' },
  { severity: 'medium', label: 'medium → warning', accent: '#EAB308', bg: '#FEF9C3', text: '#854D0E' },
  { severity: 'low', label: 'low → ok', accent: '#16A34A', bg: '#DCFCE7', text: '#166534' },
]

const ALL_SEVERITIES: { severity: Severity; label: string }[] = [
  { severity: 'critical', label: 'Критично' },
  { severity: 'high', label: 'Высокий' },
  { severity: 'medium', label: 'Средний' },
  { severity: 'low', label: 'Низкий' },
]

// ── Демо-данные DataTable: 5 фейковых инцидентов ──────────────────────────────
interface DemoRow {
  id: string
  severity: Severity
  label: string
  object: string
  score: number
  time: string
}

const DEMO_ROWS: DemoRow[] = [
  { id: 'INC-1042', severity: 'critical', label: 'Критично', object: 'А 482 ТР 716', score: 97, time: '14:02' },
  { id: 'INC-1041', severity: 'high', label: 'Высокий', object: 'В 217 КН 102', score: 84, time: '13:51' },
  { id: 'INC-1039', severity: 'medium', label: 'Средний', object: 'Е 905 ОС 716', score: 55, time: '13:30' },
  { id: 'INC-1037', severity: 'low', label: 'Низкий', object: 'К 110 АА 716', score: 20, time: '12:58' },
  { id: 'INC-1035', severity: 'high', label: 'Высокий', object: 'М 641 РТ 116', score: 72, time: '12:14' },
]

const DEMO_COLUMNS: Column<DemoRow>[] = [
  { id: 'id', header: 'ID', cell: (r) => <span className="font-medium text-ink">{r.id}</span>, sortable: true, sortValue: (r) => r.id },
  { id: 'severity', header: 'Severity', cell: (r) => <SeverityBadge severity={r.severity} label={r.label} /> },
  { id: 'object', header: 'Объект', cell: (r) => r.object, sortable: true, sortValue: (r) => r.object },
  { id: 'score', header: 'Риск', align: 'right', cell: (r) => <ScoreBar score={r.score} className="w-32" />, sortable: true, sortValue: (r) => r.score },
  { id: 'time', header: 'Время', align: 'right', cell: (r) => <span className="tabular-nums text-muted">{r.time}</span>, sortable: true, sortValue: (r) => r.time },
]

// ── Демо-телеметрия: кейс «датчик удара» (скорость 54→0, пик ax при t=0) ───────
const SHOCK_TELEMETRY: TelemetryPoint[] = [
  { ts_offset: -6, speed: 54, ax: 0.1, ay: 0.0 },
  { ts_offset: -5, speed: 54, ax: -0.2, ay: 0.1 },
  { ts_offset: -4, speed: 53, ax: -0.4, ay: -0.1 },
  { ts_offset: -3, speed: 52, ax: -0.8, ay: 0.2 },
  { ts_offset: -2, speed: 49, ax: -1.6, ay: 0.3 },
  { ts_offset: -1, speed: 41, ax: -4.2, ay: 0.6 },
  { ts_offset: 0, speed: 12, ax: -24.5, ay: 3.1 },
  { ts_offset: 1, speed: 2, ax: -6.0, ay: -1.2 },
  { ts_offset: 2, speed: 0, ax: -0.4, ay: 0.2 },
  { ts_offset: 3, speed: 0, ax: 0.1, ay: 0.0 },
  { ts_offset: 4, speed: 0, ax: 0.0, ay: 0.0 },
  { ts_offset: 5, speed: 0, ax: 0.0, ay: 0.0 },
  { ts_offset: 6, speed: 0, ax: 0.0, ay: 0.0 },
]

// Демо-источник для VideoPlayer (внешний сэмпл; в проде — fixture/архив).
const DEMO_VIDEO_SRC =
  'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'

// ── Хелперы вёрстки витрины ───────────────────────────────────────────────────
function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-ink">{title}</h2>
        {hint && <p className="mt-0.5 text-sm text-muted">{hint}</p>}
      </div>
      {children}
    </section>
  )
}

function Swatch({ name, value, hex, dark }: { name: string; value: string; hex: string; dark?: boolean }) {
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <div
        className="flex h-16 items-end p-2"
        style={{ background: value, color: dark ? '#FFFFFF' : '#0F172A' }}
      >
        <span className="text-xs font-medium">{name}</span>
      </div>
      <div className="bg-surface px-2 py-1.5 font-mono text-[11px] uppercase text-muted">{hex}</div>
    </div>
  )
}

export default function StyleGuide() {
  const [selectedCard, setSelectedCard] = useState<Severity | null>('critical')
  const [selectedRow, setSelectedRow] = useState<string>('INC-1042')

  return (
    <div className="min-h-screen bg-bg px-8 py-10 font-sans text-ink">
      <div className="mx-auto max-w-6xl space-y-12">
        <header className="space-y-1">
          <h1 className="text-[32px] font-bold leading-tight">SKAI Online — Style Guide</h1>
          <p className="text-sm text-muted">
            Витрина UI-примитивов (d2) во всех состояниях. Источник истины — init/context/DESIGN.md.
          </p>
        </header>

        {/* ── Палитра ─────────────────────────────────────────────────────── */}
        <Section title="Палитра" hint="Токены d1 (tokens.css / tailwind.config.ts)">
          <div className="space-y-6">
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Базовая</h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
                {BASE_TOKENS.map((t) => (
                  <Swatch key={t.name} name={t.name} value={`var(${t.cssVar})`} hex={t.hex} dark={!t.onLight} />
                ))}
              </div>
            </div>
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
                Severity (accent · bg · text)
              </h3>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {SEVERITY_TOKENS.map((s) => (
                  <div key={s.severity} className="space-y-2 rounded-md border border-border bg-surface p-3">
                    <div className="text-xs font-semibold text-ink">{s.label}</div>
                    <div className="grid grid-cols-3 gap-2">
                      <Swatch name="accent" value={s.accent} hex={s.accent} dark />
                      <Swatch name="bg" value={s.bg} hex={s.bg} />
                      <Swatch name="text" value={s.text} hex={s.text} dark />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Section>

        {/* ── Кнопки ──────────────────────────────────────────────────────── */}
        <Section title="Button" hint="variant · icon · loading · disabled · icon-only">
          <Card>
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary">Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="danger">Danger</Button>
              <Button variant="ghost">Ghost</Button>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button variant="primary" icon={Check}>
                С иконкой
              </Button>
              <Button variant="secondary" icon={Download}>
                Скачать
              </Button>
              <Button variant="primary" loading>
                Загрузка
              </Button>
              <Button variant="primary" disabled>
                Disabled
              </Button>
              <Button variant="danger" icon={Phone} aria-label="Позвонить" />
            </div>
          </Card>
        </Section>

        {/* ── SeverityBadge ───────────────────────────────────────────────── */}
        <Section title="SeverityBadge" hint="4 уровня · маппинг API→токен (medium→warning, low→ok)">
          <Card>
            <div className="flex flex-wrap items-center gap-3">
              {ALL_SEVERITIES.map((s) => (
                <SeverityBadge key={s.severity} severity={s.severity} label={s.label} />
              ))}
            </div>
          </Card>
        </Section>

        {/* ── ScoreBar ────────────────────────────────────────────────────── */}
        <Section title="ScoreBar" hint="score 20 / 55 / 84 / 97 — заливка зелёный→жёлтый→красный">
          <Card className="max-w-md space-y-3">
            {[20, 55, 84, 97].map((score) => (
              <ScoreBar key={score} score={score} />
            ))}
          </Card>
        </Section>

        {/* ── Card ────────────────────────────────────────────────────────── */}
        <Section title="Card" hint="default · incident (severity, hover, selected — кликни по карточке)">
          <div className="space-y-4">
            <Card>
              <h3 className="text-lg font-semibold text-ink">Обычная карточка</h3>
              <p className="mt-1 text-sm text-muted">
                variant=&quot;default&quot;, padding 20px, без цветной полосы.
              </p>
            </Card>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {ALL_SEVERITIES.map((s) => (
                <Card
                  key={s.severity}
                  variant="incident"
                  severity={s.severity}
                  selected={selectedCard === s.severity}
                  onClick={() => setSelectedCard(s.severity)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-ink">Инцидент · {s.label}</span>
                    <SeverityBadge severity={s.severity} label={s.label} />
                  </div>
                  <p className="mt-1 text-sm text-muted">
                    incident · border-left по severity · {selectedCard === s.severity ? 'selected' : 'наведи / кликни'}
                  </p>
                </Card>
              ))}
            </div>
          </div>
        </Section>

        {/* ── VideoPlayer ─────────────────────────────────────────────────── */}
        <Section title="VideoPlayer" hint="демо-src (с меткой события) · пустое состояние">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <VideoPlayer src={DEMO_VIDEO_SRC} eventMarkerPct={40} />
              <span className="text-xs text-muted">src + eventMarkerPct=40</span>
            </div>
            <div className="space-y-1">
              <VideoPlayer />
              <span className="text-xs text-muted">пустое состояние (src отсутствует)</span>
            </div>
          </div>
        </Section>

        {/* ── DataTable ───────────────────────────────────────────────────── */}
        <Section title="DataTable" hint="5 строк · сортировка по колонкам · выделение строки">
          <Card className="p-0">
            <DataTable
              columns={DEMO_COLUMNS}
              rows={DEMO_ROWS}
              rowKey={(r) => r.id}
              selectedKey={selectedRow}
              onRowClick={(r) => setSelectedRow(r.id)}
            />
          </Card>
        </Section>

        {/* ── TelemetryChart ──────────────────────────────────────────────── */}
        <Section title="TelemetryChart" hint="кейс «датчик удара»: скорость 54→0, пик акселерометра при t=0">
          <Card>
            <TelemetryChart data={SHOCK_TELEMETRY} playheadOffset={-1} />
            <p className="mt-2 text-xs text-muted">
              Жёлтая пунктирная вертикаль — статичный маркер события (t=0). Синяя — playhead (текущее время видео).
            </p>
          </Card>
        </Section>
      </div>
    </div>
  )
}
