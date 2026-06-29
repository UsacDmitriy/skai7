import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, test, vi, beforeEach } from 'vitest'
import Hypercare from './Hypercare'
import * as client from '@/api/client'

vi.mock('@/api/client', () => ({
  getHypercareRules: vi.fn(),
  evaluateHypercare: vi.fn(),
  requestHypercare: vi.fn(),
}))

vi.mock('@/state/role', () => ({
  useRole: () => ({ role: 'security' }),
  RoleProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  navForRole: (_role: string, nav: unknown[]) => nav,
}))

const mockRules = [
  {
    id: 'R-TEST',
    name: 'Вскрытие кузова',
    enabled: true,
    role_scope: 'security',
    trigger: { kind: 'event' as const, alarm_codes: ['TRUCK_BODY'] },
    window: { before_sec: 300, after_sec: 120, mode: 'continuous' as const },
    cameras: [1, 5] as (1 | 2 | 3 | 5)[],
  },
]

const mockEvidence = [
  {
    id: 'ev-1',
    rule_id: 'R-TEST',
    rule_name: 'Вскрытие кузова',
    vehicle_plate: 'А001АА77',
    trigger_ts: '2026-06-29T10:00:00',
    trigger_label: 'Вскрытие (TRUCK_BODY)',
    status: 'fulfilled' as const,
    items: [] as [],
  },
]

beforeEach(() => {
  vi.mocked(client.getHypercareRules).mockResolvedValue(mockRules)
  vi.mocked(client.evaluateHypercare).mockResolvedValue(mockEvidence)
  vi.mocked(client.requestHypercare).mockResolvedValue(mockEvidence[0])
})

describe('Hypercare page', () => {
  test('renders page title', async () => {
    render(<Hypercare />)
    expect(screen.getByText('Гиперопека')).toBeTruthy()
  })

  test('loads and displays rules after mount', async () => {
    render(<Hypercare />)
    await waitFor(() => expect(client.getHypercareRules).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText('Вскрытие кузова')).toBeTruthy())
  })

  test('switching to evidence tab triggers evaluateHypercare', async () => {
    render(<Hypercare />)
    await waitFor(() => expect(client.getHypercareRules).toHaveBeenCalled())
    fireEvent.click(screen.getByText('Доказательства'))
    await waitFor(() => expect(client.evaluateHypercare).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText('А001АА77')).toBeTruthy())
  })

  test('switching to request tab shows RuleBuilder', () => {
    render(<Hypercare />)
    fireEvent.click(screen.getByText('Запрос'))
    expect(screen.getByLabelText('Гос. номер ТС')).toBeTruthy()
  })

  test('toggling rule updates active count', async () => {
    render(<Hypercare />)
    await waitFor(() => expect(screen.getByText('Вскрытие кузова')).toBeTruthy())
    expect(screen.getByText(/1 правил активно/)).toBeTruthy()
  })
})
