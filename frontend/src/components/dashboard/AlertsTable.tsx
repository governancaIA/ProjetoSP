import { useNavigate } from 'react-router-dom'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatBRL, truncateChave, SEVERITY_STYLES } from '@/lib/utils'
import type { Alert } from '@/types/api'

interface AlertsTableProps {
  alerts: Alert[]
  loading?: boolean
}

export function AlertsTable({ alerts, loading }: AlertsTableProps) {
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

  if (!alerts || alerts.length === 0) {
    return <p className="text-center text-slate-500 py-8">Nenhum alerta encontrado</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Severidade</TableHead>
          <TableHead>Regra</TableHead>
          <TableHead>Chave NF</TableHead>
          <TableHead className="text-right">Exposição</TableHead>
          <TableHead>Mensagem</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {alerts.map((alert) => (
          <TableRow
            key={`${alert.fiscal_document_id}-${alert.rule_id}`}
            className="cursor-pointer hover:bg-slate-50"
            onClick={() => navigate(`/documents/${alert.fiscal_document_id}`)}
          >
            <TableCell>
              <Badge variant="outline" className={SEVERITY_STYLES[alert.severity]}>
                {alert.severity}
              </Badge>
            </TableCell>
            <TableCell className="font-mono text-xs">{alert.rule_id}</TableCell>
            <TableCell className="font-mono text-xs">{truncateChave(alert.document_chave)}</TableCell>
            <TableCell className="text-right font-semibold text-red-600">
              {formatBRL(alert.exposure)}
            </TableCell>
            <TableCell className="max-w-xs truncate text-sm">{alert.message}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
