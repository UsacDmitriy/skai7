import { type ReactNode, useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react'
import { cn } from './cn'

export interface Column<T> {
  /** Стабильный идентификатор колонки (ключ сортировки/реакта). */
  id: string
  header: ReactNode
  /** Рендер ячейки строки. */
  cell: (row: T) => ReactNode
  align?: 'left' | 'right' | 'center'
  sortable?: boolean
  /** Значение для сортировки (если колонка sortable). */
  sortValue?: (row: T) => string | number
}

export interface DataTableProps<T> {
  columns: Column<T>[]
  rows: T[]
  /** Уникальный ключ строки. */
  rowKey: (row: T) => string
  /** Ключ выделенной строки (подсветка bg primary-50). */
  selectedKey?: string
  onRowClick?: (row: T) => void
  /** Текст пустого состояния. */
  emptyLabel?: string
  className?: string
}

type SortState = { id: string; dir: 'asc' | 'desc' } | null

const ALIGN: Record<NonNullable<Column<unknown>['align']>, string> = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  selectedKey,
  onRowClick,
  emptyLabel = 'Нет данных',
  className,
}: DataTableProps<T>) {
  const [sort, setSort] = useState<SortState>(null)

  const sortedRows = useMemo(() => {
    if (!sort) return rows
    const col = columns.find((c) => c.id === sort.id)
    if (!col?.sortValue) return rows
    const getValue = col.sortValue
    return [...rows].sort((a, b) => {
      const va = getValue(a)
      const vb = getValue(b)
      const cmp = va < vb ? -1 : va > vb ? 1 : 0
      return sort.dir === 'asc' ? cmp : -cmp
    })
  }, [rows, columns, sort])

  const toggleSort = (col: Column<T>) => {
    if (!col.sortable) return
    setSort((prev) => {
      if (prev?.id !== col.id) return { id: col.id, dir: 'asc' }
      return prev.dir === 'asc' ? { id: col.id, dir: 'desc' } : null
    })
  }

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b-2 border-border bg-bg">
            {columns.map((col) => {
              const active = sort?.id === col.id
              return (
                <th
                  key={col.id}
                  onClick={() => toggleSort(col)}
                  className={cn(
                    'px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted',
                    ALIGN[col.align ?? 'left'],
                    col.sortable && 'cursor-pointer select-none hover:text-ink',
                  )}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortable &&
                      (!active ? (
                        <ChevronsUpDown size={12} className="text-muted" aria-hidden />
                      ) : sort?.dir === 'asc' ? (
                        <ChevronUp size={12} aria-hidden />
                      ) : (
                        <ChevronDown size={12} aria-hidden />
                      ))}
                  </span>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-3 py-8 text-center text-muted">
                {emptyLabel}
              </td>
            </tr>
          ) : (
            sortedRows.map((row) => {
              const key = rowKey(row)
              const selected = key === selectedKey
              return (
                <tr
                  key={key}
                  onClick={() => onRowClick?.(row)}
                  className={cn(
                    'border-b border-border transition-colors',
                    onRowClick && 'cursor-pointer',
                    selected ? 'bg-primary-50' : onRowClick && 'hover:bg-bg',
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.id}
                      className={cn('px-3 py-2 text-ink', ALIGN[col.align ?? 'left'])}
                    >
                      {col.cell(row)}
                    </td>
                  ))}
                </tr>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  )
}
