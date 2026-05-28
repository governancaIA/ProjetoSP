import { useQuery } from '@tanstack/react-query'
import { fetchFornecedorRanking } from '@/services/api'

export function useFornecedorRanking(limit = 10) {
  return useQuery({
    queryKey: ['fornecedor-ranking', limit],
    queryFn: () => fetchFornecedorRanking(limit),
    staleTime: 5 * 60 * 1000,
  })
}
