import { describe, expect, it } from 'vitest'
import { DEFAULT_ROLE, isRole, parseStoredRole } from './role'

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
