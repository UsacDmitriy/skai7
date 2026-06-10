import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SceneContextChip } from './SceneContextChip'
import type { SceneContext } from '../../api/types'

/**
 * f15 · SceneContextChip — рендер погоды/день-ночь/покрытия по props (§8.4).
 *  • happy: лейблы погоды/времени суток/покрытия выводятся словами;
 *  • рискованное покрытие (мокро/снег/гололёд) → предупреждающий токен;
 *  • `unknown` погода/покрытие → нейтральный вид, сегмент покрытия скрыт.
 * Чистый презентационный компонент — без сети/моков, props конструируем в тесте.
 */

const scene = (over: Partial<SceneContext> = {}): SceneContext => ({
  id: 'inc-001',
  weather: 'clear',
  day_night: 'day',
  road_surface: 'dry',
  area: 'urban',
  visibility: 'good',
  scene_confidence: 0.8,
  ...over,
})

/** Корневой чип несёт title со сводкой — берём его как опорный элемент. */
function chip() {
  return screen.getByTitle(/Погода:/)
}

describe('f15 · SceneContextChip', () => {
  it('happy: погода/время суток/покрытие выводятся словами', () => {
    render(<SceneContextChip scene={scene({ weather: 'rain', day_night: 'night', road_surface: 'wet' })} />)
    expect(screen.getByText('Дождь')).toBeInTheDocument()
    expect(screen.getByText('Ночь')).toBeInTheDocument()
    expect(screen.getByText('Мокро')).toBeInTheDocument()
    expect(chip()).toHaveAttribute('title', 'Погода: Дождь, Ночь, покрытие: Мокро')
  })

  it('рискованное покрытие (мокро/снег/гололёд) → предупреждающий токен', () => {
    render(<SceneContextChip scene={scene({ road_surface: 'ice' })} />)
    expect(chip()).toHaveClass('border-warning')
    expect(chip()).not.toHaveClass('border-border')
    expect(screen.getByText('Гололёд')).toBeInTheDocument()
  })

  it('сухое покрытие → нейтральный вид (без предупреждения)', () => {
    render(<SceneContextChip scene={scene({ road_surface: 'dry' })} />)
    expect(chip()).toHaveClass('border-border')
    expect(chip()).not.toHaveClass('border-warning')
    expect(screen.getByText('Сухо')).toBeInTheDocument()
  })

  it('unknown погода → нейтральный лейбл «—», покрытие unknown скрыто', () => {
    render(<SceneContextChip scene={scene({ weather: 'unknown', road_surface: 'unknown' })} />)
    // Лейбл погоды для unknown — нейтральная заглушка «—» (единственная на чипе).
    expect(screen.getByText('—')).toBeInTheDocument()
    // Сегмент покрытия для unknown не рендерится → лейблов покрытия нет.
    expect(screen.queryByText('Сухо')).not.toBeInTheDocument()
    expect(screen.queryByText('Мокро')).not.toBeInTheDocument()
    // unknown-покрытие риском не считается → нейтральный токен.
    expect(chip()).toHaveClass('border-border')
  })
})
