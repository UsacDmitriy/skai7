import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { type Column, DataTable } from './DataTable'

/**
 * d2 · DataTable — сортировка по sortable-колонке (asc → desc → сброс) и выбор
 * строки (подсветка selectedKey + onRowClick).
 */
interface Row {
  id: string
  name: string
  score: number
}

const ROWS: Row[] = [
  { id: '1', name: 'Bravo', score: 20 },
  { id: '2', name: 'Alpha', score: 50 },
  { id: '3', name: 'Charlie', score: 10 },
]

const COLUMNS: Column<Row>[] = [
  { id: 'name', header: 'Имя', cell: (r) => r.name, sortable: true, sortValue: (r) => r.name },
  { id: 'score', header: 'Скор', cell: (r) => r.score },
]

function names(container: HTMLElement): (string | null | undefined)[] {
  return Array.from(container.querySelectorAll('tbody tr')).map(
    (tr) => tr.querySelector('td')?.textContent,
  )
}

describe('DataTable · сортировка', () => {
  it('клик по заголовку: asc → desc → сброс к исходному порядку', () => {
    const { container } = render(
      <DataTable columns={COLUMNS} rows={ROWS} rowKey={(r) => r.id} />,
    )
    expect(names(container)).toEqual(['Bravo', 'Alpha', 'Charlie'])

    const header = screen.getByRole('button', { name: /Имя/ })

    fireEvent.click(header) // asc
    expect(names(container)).toEqual(['Alpha', 'Bravo', 'Charlie'])
    expect(screen.getByRole('columnheader', { name: /Имя/ })).toHaveAttribute(
      'aria-sort',
      'ascending',
    )

    fireEvent.click(header) // desc
    expect(names(container)).toEqual(['Charlie', 'Bravo', 'Alpha'])
    expect(screen.getByRole('columnheader', { name: /Имя/ })).toHaveAttribute(
      'aria-sort',
      'descending',
    )

    fireEvent.click(header) // сброс → исходный порядок
    expect(names(container)).toEqual(['Bravo', 'Alpha', 'Charlie'])
  })

  it('несортируемая колонка не имеет кнопки-сортировки', () => {
    render(<DataTable columns={COLUMNS} rows={ROWS} rowKey={(r) => r.id} />)
    expect(screen.queryByRole('button', { name: /Скор/ })).toBeNull()
  })
})

describe('DataTable · выбор строки', () => {
  it('selectedKey подсвечивает выбранную строку', () => {
    const { container } = render(
      <DataTable columns={COLUMNS} rows={ROWS} rowKey={(r) => r.id} selectedKey="2" />,
    )
    const selected = container.querySelector('tbody tr.bg-primary-50') as HTMLElement
    expect(selected).toBeInTheDocument()
    expect(selected.textContent).toContain('Alpha')
  })

  it('onRowClick зовётся с данными строки', () => {
    const onRowClick = vi.fn()
    render(
      <DataTable columns={COLUMNS} rows={ROWS} rowKey={(r) => r.id} onRowClick={onRowClick} />,
    )
    fireEvent.click(screen.getByText('Charlie'))
    expect(onRowClick).toHaveBeenCalledWith(ROWS[2])
  })

  it('пустой список → строка emptyLabel', () => {
    render(
      <DataTable columns={COLUMNS} rows={[]} rowKey={(r) => r.id} emptyLabel="Нет данных" />,
    )
    expect(screen.getByText('Нет данных')).toBeInTheDocument()
  })
})
