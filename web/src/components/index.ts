/**
 * Публичный API библиотеки UI-примитивов SKAI Online (d2).
 * Точка входа для экранов (f4+): `import { Button, ... } from '@/components'`.
 * Витрина всех примитивов во всех состояниях — `src/pages/_StyleGuide.tsx`.
 */

export { Button } from './ui/Button'
export type { ButtonProps, ButtonVariant } from './ui/Button'

export { SeverityBadge } from './ui/SeverityBadge'
export type { SeverityBadgeProps, Severity } from './ui/SeverityBadge'

export { ScoreBar } from './ui/ScoreBar'
export type { ScoreBarProps } from './ui/ScoreBar'

export { Card } from './ui/Card'
export type { CardProps } from './ui/Card'

export { VideoPlayer } from './ui/VideoPlayer'
export type { VideoPlayerProps } from './ui/VideoPlayer'

export { DataTable } from './ui/DataTable'
export type { Column, DataTableProps } from './ui/DataTable'

export { TelemetryChart } from './ui/TelemetryChart'
export type { TelemetryChartProps, TelemetryPoint } from './ui/TelemetryChart'
