import { FileX2 } from 'lucide-react'

interface EmptyStateProps {
  message?: string
}

export function EmptyState({
  message = 'Nenhum documento importado ainda. Aguardando implementação da API.',
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <FileX2 size={64} className="text-slate-300 mb-4" />
      <p className="text-slate-500 text-center">{message}</p>
    </div>
  )
}
