import { useQuery } from '@tanstack/react-query'
import { fetchPeriodTrend } from '@/services/api'

export function usePeriodTrend(months = 12) {
  return useQuery({
    queryKey: ['period-trend', months],
    queryFn: () => fetchPeriodTrend(months),
    staleTime: 5 * 60 * 1000,
  })
}
