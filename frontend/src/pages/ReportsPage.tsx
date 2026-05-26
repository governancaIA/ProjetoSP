import { useState } from 'react'
import { Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { downloadReport } from '@/services/api'

const CURRENT_YEAR = new Date().getFullYear()
const CURRENT_MONTH = new Date().getMonth() + 1

const MONTHS = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

const YEARS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i)

export function ReportsPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [month, setMonth] = useState(CURRENT_MONTH)
  const [loadingPdf, setLoadingPdf] = useState(false)
  const [loadingExcel, setLoadingExcel] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDownload = async (format: 'pdf' | 'excel') => {
    setError(null)
    if (format === 'pdf') setLoadingPdf(true)
    else setLoadingExcel(true)

    try {
      await downloadReport(year, month, format)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erro ao gerar relatório')
    } finally {
      if (format === 'pdf') setLoadingPdf(false)
      else setLoadingExcel(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Relatórios" />

      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* Tipo de relatório */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="border-brand-200 bg-brand-50">
            <CardContent className="p-6 flex items-start gap-4">
              <FileText className="w-8 h-8 text-brand-600 mt-1 shrink-0" />
              <div>
                <h3 className="font-semibold text-lg text-slate-900">Relatório Executivo PDF</h3>
                <p className="text-slate-500 text-sm mt-1">
                  Score de risco, top inconsistências, exposição estimada em R$ e assinatura do especialista.
                  Pronto para apresentar ao contador ou ao fiscal.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="border-emerald-200 bg-emerald-50">
            <CardContent className="p-6 flex items-start gap-4">
              <FileSpreadsheet className="w-8 h-8 text-emerald-600 mt-1 shrink-0" />
              <div>
                <h3 className="font-semibold text-lg text-slate-900">Planilha Excel Detalhada</h3>
                <p className="text-slate-500 text-sm mt-1">
                  Todas as inconsistências do período com filtros automáticos.
                  Cada linha com regra, emitente, valor NF e exposição estimada.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Seleção de período e download */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Selecionar Período e Baixar</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex flex-wrap gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Mês</label>
                <select
                  value={month}
                  onChange={(e) => setMonth(Number(e.target.value))}
                  className="px-3 py-2 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {MONTHS.map((name, idx) => (
                    <option key={idx + 1} value={idx + 1}>{name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Ano</label>
                <select
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  className="px-3 py-2 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {YEARS.map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                {error}
              </p>
            )}

            <div className="flex flex-wrap gap-3">
              <Button
                onClick={() => handleDownload('pdf')}
                disabled={loadingPdf || loadingExcel}
                className="flex items-center gap-2"
              >
                {loadingPdf ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Download size={16} />
                )}
                {loadingPdf ? 'Gerando PDF...' : 'Baixar PDF Executivo'}
              </Button>

              <Button
                variant="outline"
                onClick={() => handleDownload('excel')}
                disabled={loadingPdf || loadingExcel}
                className="flex items-center gap-2"
              >
                {loadingExcel ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Download size={16} />
                )}
                {loadingExcel ? 'Gerando Excel...' : 'Exportar Excel'}
              </Button>
            </div>

            <p className="text-xs text-slate-400">
              O PDF inclui assinatura do especialista e call-to-action para consultoria.
              O Excel inclui filtros automáticos e cores por severidade.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
