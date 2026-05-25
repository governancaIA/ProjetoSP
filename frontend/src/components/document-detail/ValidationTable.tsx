import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Check, X } from 'lucide-react'
import { SEVERITY_STYLES, getSeverityLabel } from '@/lib/utils'
import type { ValidationResult } from '@/types/api'

interface ValidationTableProps {
  results: ValidationResult[]
  loading?: boolean
}

export function ValidationTable({ results, loading }: ValidationTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    )
  }

  if (!results || results.length === 0) {
    return <p className="text-center text-slate-500 py-8">Nenhum resultado de validação</p>
  }

  const failedFirst = [...results].sort((a, b) => {
    if (a.passed === b.passed) return 0
    return a.passed ? 1 : -1
  })

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Regra</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Severidade</TableHead>
          <TableHead>Mensagem</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {failedFirst.map((result) => (
          <TableRow
            key={result.rule_id}
            className={
              !result.passed && result.severity === 'CRITICAL'
                ? 'bg-red-50'
                : !result.passed && result.severity === 'WARNING'
                  ? 'bg-yellow-50'
                  : ''
            }
          >
            <TableCell className="font-mono font-semibold">{result.rule_id}</TableCell>
            <TableCell>
              {result.passed ? (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  <Check size={14} className="mr-1" /> Passou
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                  <X size={14} className="mr-1" /> Falhou
                </Badge>
              )}
            </TableCell>
            <TableCell>
              {result.severity ? (
                <Badge variant="outline" className={SEVERITY_STYLES[result.severity]}>
                  {getSeverityLabel(result.severity)}
                </Badge>
              ) : (
                <span className="text-slate-400">N/A</span>
              )}
            </TableCell>
            <TableCell className="max-w-lg">{result.message || 'Sem mensagem'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
