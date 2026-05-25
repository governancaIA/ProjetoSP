import { useQuery } from '@tanstack/react-query'
import { fetchValidationResults } from '@/services/api'

export function useValidationResults(id: number) {
  return useQuery({
    queryKey: ['validation-results', id],
    queryFn: () => fetchValidationResults(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}
