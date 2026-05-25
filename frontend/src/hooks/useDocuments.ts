import { useQuery } from '@tanstack/react-query'
import { fetchDocuments } from '@/services/api'

export function useDocuments() {
  return useQuery({
    queryKey: ['documents'],
    queryFn: () => fetchDocuments(),
    staleTime: 5 * 60 * 1000,
  })
}
