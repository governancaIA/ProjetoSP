import { useNavigate } from 'react-router-dom'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDate, truncateChave, scoreColorClass } from '@/lib/utils'
import type { Document } from '@/types/api'

interface DocumentsTableProps {
  documents: Document[]
  loading?: boolean
}

export function DocumentsTable({ documents, loading }: DocumentsTableProps) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    )
  }

  if (!documents || documents.length === 0) {
    return <p className="text-center text-slate-500 py-8">Nenhum documento encontrado</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Chave de Acesso</TableHead>
          <TableHead>NF</TableHead>
          <TableHead>Emitente</TableHead>
          <TableHead>Data</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Score</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {documents.map((doc) => (
          <TableRow
            key={doc.id}
            className="cursor-pointer hover:bg-slate-50"
            onClick={() => navigate(`/documents/${doc.id}`)}
          >
            <TableCell className="font-mono text-xs">{truncateChave(doc.chave_acesso || '')}</TableCell>
            <TableCell>{doc.numero_nf}</TableCell>
            <TableCell className="max-w-xs truncate">{doc.emitente_nome}</TableCell>
            <TableCell>{doc.data_emissao ? formatDate(doc.data_emissao) : 'N/A'}</TableCell>
            <TableCell>
              <Badge
                variant="outline"
                className={
                  doc.status_nfe === 'autorizado'
                    ? 'bg-green-50 text-green-700 border-green-200'
                    : doc.status_nfe === 'cancelado'
                      ? 'bg-red-50 text-red-700 border-red-200'
                      : 'bg-yellow-50 text-yellow-700 border-yellow-200'
                }
              >
                {doc.status_nfe || 'N/A'}
              </Badge>
            </TableCell>
            <TableCell className={`text-right font-semibold ${scoreColorClass(doc.document_score || 0)}`}>
              {doc.document_score ?? 'N/A'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
