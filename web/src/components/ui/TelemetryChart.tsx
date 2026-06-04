import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

/** Точка телеметрии — форма из CONTRACT §3.1 (`ax` = производная скорости). */
export interface TelemetryPoint {
  ts_offset: number
  speed: number
  ax: number
  ay: number
}

export interface TelemetryChartProps {
  data: TelemetryPoint[]
  /**
   * Движущаяся синяя вертикаль = текущее время видео (idea #1).
   * Не путать со статичным маркером события (x=0). undefined → не рисуется.
   */
  playheadOffset?: number
  height?: number
  className?: string
}

// Цвета — через CSS-переменные d1 (tokens.css), без прямых hex.
const COLOR_SPEED = 'var(--color-primary)' // #1E3A8A
const COLOR_ACCEL = 'var(--sev-high)' // #EA580C
const COLOR_EVENT = 'var(--sev-warning)' // #EAB308 — статичный маркер события
const COLOR_GRID = 'var(--color-border)' // #E2E8F0
const COLOR_AXIS = 'var(--color-muted)' // подписи осей

export function TelemetryChart({
  data,
  playheadOffset,
  height = 240,
  className,
}: TelemetryChartProps) {
  return (
    <div className={className} style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
          <CartesianGrid stroke={COLOR_GRID} strokeDasharray="2 2" />
          <XAxis
            dataKey="ts_offset"
            type="number"
            stroke={COLOR_AXIS}
            tick={{ fontSize: 11 }}
            tickLine={false}
            unit="с"
          />
          <YAxis
            yAxisId="speed"
            stroke={COLOR_AXIS}
            tick={{ fontSize: 11 }}
            tickLine={false}
            width={36}
          />
          <YAxis
            yAxisId="accel"
            orientation="right"
            stroke={COLOR_AXIS}
            tick={{ fontSize: 11 }}
            tickLine={false}
            width={36}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--color-surface)',
              border: `1px solid ${COLOR_GRID}`,
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          {/* Статичный маркер события — t=0 */}
          <ReferenceLine
            x={0}
            yAxisId="speed"
            stroke={COLOR_EVENT}
            strokeDasharray="4 4"
            strokeWidth={1.5}
          />
          {/* Движущийся playhead — позиция текущего времени видео */}
          {playheadOffset != null && (
            <ReferenceLine
              x={playheadOffset}
              yAxisId="speed"
              stroke={COLOR_SPEED}
              strokeWidth={2}
            />
          )}
          <Line
            yAxisId="speed"
            type="monotone"
            dataKey="speed"
            name="Скорость"
            stroke={COLOR_SPEED}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            yAxisId="accel"
            type="monotone"
            dataKey="ax"
            name="Акселерометр"
            stroke={COLOR_ACCEL}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
