import { AlertTriangle, ShieldCheck, ShieldAlert } from 'lucide-react'
import type { FornecedorRankingItem } from '@/services/api'
import { Skeleton } from '@/components/ui/skeleton'

interface FornecedorRankingProps {
  data: FornecedorRankingItem[]
  loading?: boolean
}

function RiskBar({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100)
  const color = pct >= 50 ? 'bg-red-500' : pct >= 20 ? 'bg-amber-400' : 'bg-emerald-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium tabular-nums w-8">{pct}%</span>
    </div>
  )
}

function RiskIcon({ rate }: { rate: number }) {
  if (rate >= 0.5) return <ShieldAlert size={14} className="text-red-500 shrink-0" />
  if (rate >= 0.2) return <AlertTriangle size={14} className="text-amber-500 shrink-0" />
  return <ShieldCheck size={14} className="text-emerald-500 shrink-0" />
}

const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

export function FornecedorRanking({ data, loading }: FornecedorRankingProps) {
  if (loading) return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
    </div>
  )

  if (!data.length) return (
    <p className="text-sm text-slate-400 text-center py-6">Nenhum fornecedor com documentos processados</p>
  )

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            <th className="pb-2 text-left font-medium text-slate-500 text-xs">#</th>
            <th className="pb-2 text-left font-medium text-slate-500 text-xs">Fornecedor</th>
            <th className="pb-2 text-left font-medium text-slate-500 text-xs">Taxa Falha</th>
            <th className="pb-2 text-right font-medium text-slate-500 text-xs">NFs</th>
            <th className="pb-2 text-right font-medium text-slate-500 text-xs">Volume</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={row.emitente_cnpj_masked} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
              <td className="py-2 pr-2 text-slate-400 text-xs tabular-nums">{i + 1}</td>
              <td className="py-2 pr-3 max-w-[160px]">
                <div className="flex items-center gap-1.5">
                  <RiskIcon rate={row.failure_rate} />
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-700 text-xs leading-tight">
                      {row.emitente_nome !== '–' ? row.emitente_nome : row.emitente_cnpj_masked}
                    </p>
                    {row.emitente_nome !== '–' && (
                      <p className="text-slate-400 text-[10px] font-mono">{row.emitente_cnpj_masked}</p>
                    )}
                  </div>
                </div>
              </td>
              <td className="py-2 pr-3">
                <RiskBar rate={row.failure_rate} />
              </td>
              <td className="py-2 pr-3 text-right text-xs tabular-nums text-slate-600">
                <span className="text-red-600 font-medium">{row.docs_com_falha}</span>
                <span className="text-slate-400">/{row.total_nfs}</span>
              </td>
              <td className="py-2 text-right text-xs tabular-nums text-slate-500">
                {BRL.format(row.total_valor)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
