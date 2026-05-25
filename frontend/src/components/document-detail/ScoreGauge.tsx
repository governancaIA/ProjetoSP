import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from 'recharts'
import { scoreColorClass } from '@/lib/utils'

interface ScoreGaugeProps {
  score: number
}

export function ScoreGauge({ score }: ScoreGaugeProps) {
  const data = [
    { name: 'Score', value: score, fill: '#3b82f6' },
  ]

  const color = score >= 80 ? '#16a34a' : score >= 60 ? '#ca8a04' : '#dc2626'

  return (
    <div className="flex flex-col items-center">
      <ResponsiveContainer width="100%" height={200}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="70%"
          outerRadius="100%"
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            background
            dataKey="value"
            cornerRadius={10}
            fill={color}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="text-center -mt-16">
        <div className={`text-4xl font-bold ${scoreColorClass(score)}`}>
          {score}
        </div>
        <p className="text-sm text-slate-500">Risco Fiscal</p>
      </div>
    </div>
  )
}
