import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import type { PeriodTrendPoint } from '@/services/api'
import { Skeleton } from '@/components/ui/skeleton'

interface TrendChartProps {
  data: PeriodTrendPoint[]
  loading?: boolean
}

const MONTH_ABBR = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

function formatPeriod(period: string) {
  const [, month] = period.split('-')
  return MONTH_ABBR[parseInt(month, 10) - 1] ?? period
}

function scoreColor(score: number) {
  if (score >= 75) return '#16a34a'
  if (score >= 50) return '#d97706'
  return '#dc2626'
}

interface TooltipPayload {
  payload: PeriodTrendPoint
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const color = scoreColor(d.period_score)
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-md text-xs space-y-1">
      <p className="font-semibold text-slate-700">{d.period}</p>
      <p style={{ color }} className="font-bold text-sm">Score: {d.period_score}/100</p>
      <p className="text-slate-500">
        Exposição: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(d.total_exposure)}
      </p>
      <p className="text-slate-500">Docs: {d.documents_processed} · Críticos: {d.critical_documents}</p>
    </div>
  )
}

export function TrendChart({ data, loading }: TrendChartProps) {
  if (loading) return <Skeleton className="h-48 w-full" />
  if (!data.length) return (
    <p className="text-sm text-slate-400 text-center py-8">Nenhum dado disponível</p>
  )

  // Color each dot based on its score
  const chartData = data.map((d) => ({ ...d, label: formatPeriod(d.period) }))

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={75} stroke="#16a34a" strokeDasharray="4 2" strokeOpacity={0.4} />
        <ReferenceLine y={50} stroke="#d97706" strokeDasharray="4 2" strokeOpacity={0.4} />
        <Line
          type="monotone"
          dataKey="period_score"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={(props) => {
            const { cx, cy, payload } = props as { cx: number; cy: number; payload: PeriodTrendPoint }
            return (
              <circle
                key={`dot-${payload.period}`}
                cx={cx}
                cy={cy}
                r={4}
                fill={scoreColor(payload.period_score)}
                stroke="#fff"
                strokeWidth={2}
              />
            )
          }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
