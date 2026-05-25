interface PeriodSelectorProps {
  year: number
  month: number
  onChange: (year: number, month: number) => void
}

export function PeriodSelector({ year, month, onChange }: PeriodSelectorProps) {
  const months = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril',
    'Maio', 'Junho', 'Julho', 'Agosto',
    'Setembro', 'Outubro', 'Novembro', 'Dezembro'
  ]

  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: 3 }, (_, i) => currentYear - 2 + i)

  return (
    <div className="flex items-center gap-3">
      <select
        value={year}
        onChange={(e) => onChange(+e.target.value, month)}
        className="rounded border border-slate-300 px-3 py-2 text-sm"
      >
        {years.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>
      <select
        value={month}
        onChange={(e) => onChange(year, +e.target.value)}
        className="rounded border border-slate-300 px-3 py-2 text-sm"
      >
        {months.map((m, i) => (
          <option key={i + 1} value={i + 1}>
            {m}
          </option>
        ))}
      </select>
    </div>
  )
}
