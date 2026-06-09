import { Sun, CloudRain, CloudSnow, CloudFog, Cloud, Moon, Sunset } from 'lucide-react'
import { cn } from '../ui/cn'
import type { SceneContext, SceneWeather, DayNight, RoadSurface } from '../../api/types'

export interface SceneContextChipProps {
  scene: SceneContext
  className?: string
}

const WEATHER_ICON: Record<SceneWeather, React.ElementType> = {
  clear: Sun,
  rain: CloudRain,
  snow: CloudSnow,
  fog: CloudFog,
  unknown: Cloud,
}

const WEATHER_LABEL: Record<SceneWeather, string> = {
  clear: 'Ясно',
  rain: 'Дождь',
  snow: 'Снег',
  fog: 'Туман',
  unknown: '—',
}

const DAYNIGHT_ICON: Record<DayNight, React.ElementType> = {
  day: Sun,
  twilight: Sunset,
  night: Moon,
}

const DAYNIGHT_LABEL: Record<DayNight, string> = {
  day: 'День',
  twilight: 'Сумерки',
  night: 'Ночь',
}

const SURFACE_LABEL: Record<RoadSurface, string> = {
  dry: 'Сухо',
  wet: 'Мокро',
  snow: 'Снег',
  ice: 'Гололёд',
  unknown: '—',
}

/** Дорожное покрытие с повышенным риском → предупреждающий токен. */
function isRiskySurface(surface: RoadSurface): boolean {
  return surface === 'wet' || surface === 'snow' || surface === 'ice'
}

export function SceneContextChip({ scene, className }: SceneContextChipProps) {
  const WeatherIcon = WEATHER_ICON[scene.weather] ?? Cloud
  const DayNightIcon = DAYNIGHT_ICON[scene.day_night] ?? Sun
  const risky = isRiskySurface(scene.road_surface)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-xl px-2 py-0.5 text-xs font-medium border',
        risky
          ? 'bg-warning-bg text-warning-text border-warning'
          : 'bg-surface text-muted border-border',
        className,
      )}
      title={`Погода: ${WEATHER_LABEL[scene.weather]}, ${DAYNIGHT_LABEL[scene.day_night]}, покрытие: ${SURFACE_LABEL[scene.road_surface]}`}
    >
      <WeatherIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{WEATHER_LABEL[scene.weather]}</span>
      <span className="opacity-40" aria-hidden>·</span>
      <DayNightIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{DAYNIGHT_LABEL[scene.day_night]}</span>
      {scene.road_surface !== 'unknown' && (
        <>
          <span className="opacity-40" aria-hidden>·</span>
          <span>{SURFACE_LABEL[scene.road_surface]}</span>
        </>
      )}
    </span>
  )
}
