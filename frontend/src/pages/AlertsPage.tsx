import { useState } from 'react'
import { AlertTriangle, Filter, RefreshCw } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { fetchAlerts, type AlertsFilter } from '@/services/api'
import type { AlertDetail } from '@/types/api'

type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIVE'

const SEVERITY_CONFIG: Record<Severity, { label: string; className: string }> = {
  CRITICAL: { label: 'Crítico', className: 'bg-red-100 text-red-800 border-red-200' },
  HIGH: { label: 'Alto', className: 'bg-orange-100 text-orange-800 border-orange-200' },
  MEDIUM: { label: 'Médio', className: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  LOW: { label: 'Baixo', className: 'bg-blue-100 text-blue-800 border-blue-200' },
  INFORMATIVE: { label: 'Info', className: 'bg-slate-100 text-slate-700 border-slate-200' },
}

const SEVERITY_OPTIONS: Severity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIVE']

function SeverityBadge({ severity }: { severity: string }) {
  const config = SEVERITY_CONFIG[severity as Severity] ?? SEVERITY_CONFIG.INFORMATIVE
  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  )
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function formatDate(iso: string | null) {
  if (!iso) return '–'
  return new Date(iso).toLocaleDateString('pt-BR')
}

function AlertRow({ alert }: { alert: AlertDetail }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <tr
        className="border-b hover:bg-slate-50 cursor-pointer transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3">
          <SeverityBadge severity={alert.severity} />
        </td>
        <td className="px-4 py-3 font-mono text-xs text-slate-600">{alert.rule_id}</td>
        <td className="px-4 py-3 text-sm text-slate-700">{alert.emitente_nome ?? '–'}</td>
        <td className="px-4 py-3 text-sm text-slate-500">{formatDate(alert.data_emissao)}</td>
        <td className="px-4 py-3 text-sm text-right font-medium">
          {formatCurrency(alert.document_value)}
        </td>
        <td className="px-4 py-3 text-sm text-right font-semibold text-red-700">
          {formatCurrency(alert.exposure)}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-amber-50">
          <td colSpan={6} className="px-4 py-3 text-sm text-slate-700 border-b">
            <p className="font-medium mb-1">Detalhes do alerta</p>
            <p className="mb-1">
              <span className="text-slate-500">Regra:</span> {alert.rule_id} v{alert.rule_version}
            </p>
            {alert.document_chave && (
              <p className="mb-1">
                <span className="text-slate-500">Chave acesso:</span>{' '}
                <span className="font-mono">{alert.document_chave}</span>
              </p>
            )}
            {alert.message && (
              <p>
                <span className="text-slate-500">Mensagem:</span> {alert.message}
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

export function AlertsPage() {
  const [filter, setFilter] = useState<AlertsFilter>({ page: 1, page_size: 50 })
  const [selectedSeverities, setSelectedSeverities] = useState<Severity[]>([])

  const activeFilter: AlertsFilter = {
    ...filter,
    severity: selectedSeverities.length > 0 ? selectedSeverities : undefined,
  }

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['alerts', activeFilter],
    queryFn: () => fetchAlerts(activeFilter),
    staleTime: 30_000,
  })

  const toggleSeverity = (s: Severity) => {
    setSelectedSeverities((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    )
    setFilter((f) => ({ ...f, page: 1 }))
  }

  const alerts = data?.alerts ?? []
  const total = data?.total ?? 0
  const pages = data?.pages ?? 1

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Alertas Fiscais">
        <Button
          size="sm"
          variant="outline"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw size={16} className={`mr-2 ${isFetching ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </TopBar>

      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* Filters */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Filter size={16} />
              Filtros
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-sm text-slate-500 mr-1">Severidade:</span>
              {SEVERITY_OPTIONS.map((s) => {
                const active = selectedSeverities.includes(s)
                const config = SEVERITY_CONFIG[s]
                return (
                  <button
                    key={s}
                    onClick={() => toggleSeverity(s)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                      active
                        ? config.className + ' ring-2 ring-offset-1 ring-current'
                        : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {config.label}
                  </button>
                )
              })}
              {selectedSeverities.length > 0 && (
                <button
                  onClick={() => setSelectedSeverities([])}
                  className="text-xs text-slate-400 hover:text-slate-600 ml-2"
                >
                  Limpar
                </button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle size={16} className="text-amber-500" />
              {isLoading ? 'Carregando...' : `${total} alerta${total !== 1 ? 's' : ''} encontrado${total !== 1 ? 's' : ''}`}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {alerts.length === 0 && !isLoading ? (
              <div className="text-center py-16 text-slate-400">
                <AlertTriangle size={40} className="mx-auto mb-3 opacity-30" />
                <p className="font-medium">Nenhum alerta encontrado</p>
                <p className="text-sm mt-1">Ajuste os filtros ou importe documentos fiscais.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-slate-50 text-left">
                      <th className="px-4 py-3 font-medium text-slate-600">Severidade</th>
                      <th className="px-4 py-3 font-medium text-slate-600">Regra</th>
                      <th className="px-4 py-3 font-medium text-slate-600">Emitente</th>
                      <th className="px-4 py-3 font-medium text-slate-600">Data Emissão</th>
                      <th className="px-4 py-3 font-medium text-slate-600 text-right">Valor NF</th>
                      <th className="px-4 py-3 font-medium text-slate-600 text-right">Exposição</th>
                    </tr>
                  </thead>
                  <tbody>
                    {isLoading
                      ? Array.from({ length: 5 }).map((_, i) => (
                          <tr key={i} className="border-b">
                            {Array.from({ length: 6 }).map((_, j) => (
                              <td key={j} className="px-4 py-3">
                                <div className="h-4 bg-slate-100 rounded animate-pulse" />
                              </td>
                            ))}
                          </tr>
                        ))
                      : alerts.map((alert) => <AlertRow key={alert.alert_id} alert={alert} />)}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>
              Página {filter.page} de {pages}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={(filter.page ?? 1) <= 1 || isFetching}
                onClick={() => setFilter((f) => ({ ...f, page: (f.page ?? 1) - 1 }))}
              >
                Anterior
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={(filter.page ?? 1) >= pages || isFetching}
                onClick={() => setFilter((f) => ({ ...f, page: (f.page ?? 1) + 1 }))}
              >
                Próxima
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
