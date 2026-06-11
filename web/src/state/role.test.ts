import { describe, expect, it } from 'vitest'
import {
  DEFAULT_ROLE,
  isRole,
  navForRole,
  parseStoredRole,
  type Role,
} from './role'

describe('isRole', () => {
  it('распознаёт валидные роли', () => {
    expect(isRole('logist')).toBe(true)
    expect(isRole('dispatcher')).toBe(true)
    expect(isRole('security')).toBe(true)
  })

  it('отвергает невалидные значения', () => {
    expect(isRole('admin')).toBe(false)
    expect(isRole('')).toBe(false)
    expect(isRole(null)).toBe(false)
    expect(isRole(undefined)).toBe(false)
    expect(isRole(42)).toBe(false)
  })
})

describe('parseStoredRole', () => {
  it('возвращает сохранённую валидную роль', () => {
    expect(parseStoredRole('security')).toBe('security')
    expect(parseStoredRole('logist')).toBe('logist')
  })

  it('повреждённое/неизвестное значение → дефолт «Диспетчер»', () => {
    expect(parseStoredRole('garbage')).toBe(DEFAULT_ROLE)
    expect(parseStoredRole('"security"')).toBe(DEFAULT_ROLE) // не разворачиваем JSON-кавычки
  })

  it('отсутствующее значение (null) → дефолт', () => {
    expect(parseStoredRole(null)).toBe(DEFAULT_ROLE)
    expect(DEFAULT_ROLE).toBe('dispatcher')
  })
})

describe('navForRole (f24)', () => {
  type Item = { to: string; roles?: Role[] }
  type Group = { title: string; items: Item[]; roles?: Role[] }

  const NAV: Group[] = [
    { title: 'Мониторинг', items: [{ to: '/monitor' }, { to: '/safety' }] },
    {
      title: 'AI',
      items: [
        { to: '/copilot' },
        { to: '/admin', roles: ['security'] },
      ],
    },
  ]

  it('пункт без `roles` виден всем ролям', () => {
    for (const role of ['logist', 'dispatcher', 'security'] as Role[]) {
      const monitor = navForRole(role, NAV).find((g) => g.title === 'Мониторинг')
      expect(monitor?.items.map((i) => i.to)).toEqual(['/monitor', '/safety'])
    }
  })

  it('пункт с `roles` виден только перечисленным', () => {
    const ai = (role: Role) =>
      navForRole(role, NAV)
        .find((g) => g.title === 'AI')
        ?.items.map((i) => i.to)
    expect(ai('security')).toEqual(['/copilot', '/admin'])
    expect(ai('logist')).toEqual(['/copilot'])
    expect(ai('dispatcher')).toEqual(['/copilot'])
  })

  it('группа с `roles` целиком скрыта для прочих ролей', () => {
    const scoped: Group[] = [
      { title: 'AI', items: [{ to: '/copilot' }], roles: ['dispatcher'] },
    ]
    expect(navForRole('dispatcher', scoped)).toHaveLength(1)
    expect(navForRole('logist', scoped)).toEqual([])
  })

  it('пустые после фильтра группы отбрасываются', () => {
    const scoped: Group[] = [
      { title: 'Только безопасник', items: [{ to: '/x', roles: ['security'] }] },
    ]
    expect(navForRole('logist', scoped)).toEqual([])
    expect(navForRole('security', scoped)).toHaveLength(1)
  })

  it('не мутирует вход', () => {
    const snapshot = JSON.stringify(NAV)
    navForRole('logist', NAV)
    expect(JSON.stringify(NAV)).toBe(snapshot)
  })

  it('неизвестная роль не роняет — показывает дефолт-видимые пункты', () => {
    const result = navForRole('admin' as Role, NAV)
    expect(result.find((g) => g.title === 'Мониторинг')?.items).toHaveLength(2)
    expect(result.find((g) => g.title === 'AI')?.items.map((i) => i.to)).toEqual([
      '/copilot',
    ])
  })
})
