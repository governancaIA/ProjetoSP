import { useQuery } from '@tanstack/react-query'
import { fetchDocumentScore } from '@/services/api'

export function useDocumentScore(id: number) {
  return useQuery({
    queryKey: ['document-score', id],
    queryFn: () => fetchDocumentScore(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}
