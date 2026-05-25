import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts'
import { Skeleton } from '@/components/ui/skeleton'
import { SEVERITY_COLOR } from '@/lib/utils'
import type { AlertsBySeverity } from '@/types/api'

interface SeverityChartProps {
  data: AlertsBySeverity
  loading?: boolean
}

export function SeverityChart({ data, loading }: SeverityChartProps) {
  if (loading) {
    return <Skeleton className="h-64" />
  }

  const chartData = [
    { name: 'Crítico', value: data.CRITICAL, fill: SEVERITY_COLOR.CRITICAL },
    { name: 'Alto', value: data.HIGH, fill: SEVERITY_COLOR.HIGH },
    { name: 'Médio', value: data.MEDIUM, fill: SEVERITY_COLOR.MEDIUM },
    { name: 'Baixo', value: data.LOW, fill: SEVERITY_COLOR.LOW },
  ].filter((d) => d.value > 0)

  if (chartData.length === 0) {
    return <p className="text-center text-slate-500 py-8">Sem dados de alerta</p>
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          outerRadius={100}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip formatter={(value) => `${value} alerta(s)`} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}
