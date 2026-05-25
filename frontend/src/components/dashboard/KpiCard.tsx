import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { scoreColorClass, scoreBgClass } from '@/lib/utils'

interface KpiCardProps {
  title: string
  value: string | number
  subtitle?: string
  variant: 'score' | 'currency' | 'count'
  score?: number
  loading?: boolean
}

export function KpiCard({
  title,
  value,
  subtitle,
  variant,
  score,
  loading,
}: KpiCardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardDescription>{title}</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-24" />
        </CardContent>
      </Card>
    )
  }

  const scoreClass = score !== undefined ? scoreColorClass(score) : ''
  const scoreBg = score !== undefined ? scoreBgClass(score) : ''

  return (
    <Card className={variant === 'score' && score !== undefined ? scoreBg : ''}>
      <CardHeader>
        <CardDescription>{title}</CardDescription>
        <CardTitle className={variant === 'score' && score !== undefined ? scoreClass : ''}>
          {value}
        </CardTitle>
        {subtitle && <CardDescription>{subtitle}</CardDescription>}
      </CardHeader>
    </Card>
  )
}
