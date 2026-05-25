import { useQuery } from '@tanstack/react-query'
import { fetchPeriodScore } from '@/services/api'

export function usePeriodScore(year: number, month: number) {
  return useQuery({
    queryKey: ['period-score', year, month],
    queryFn: () => fetchPeriodScore(year, month),
    staleTime: 5 * 60 * 1000,
  })
}
