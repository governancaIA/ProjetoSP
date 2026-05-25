import { useQuery } from '@tanstack/react-query'
import { fetchAlertQueue } from '@/services/api'

export function useAlertQueue(limit = 10) {
  return useQuery({
    queryKey: ['alert-queue', limit],
    queryFn: () => fetchAlertQueue(limit),
    staleTime: 60 * 1000,
  })
}
