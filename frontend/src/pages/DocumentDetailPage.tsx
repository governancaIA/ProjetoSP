import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TopBar } from '@/components/layout/TopBar'
import { ScoreGauge } from '@/components/document-detail/ScoreGauge'
import { ValidationTable } from '@/components/document-detail/ValidationTable'
import { useDocumentScore } from '@/hooks/useDocumentScore'
import { useValidationResults } from '@/hooks/useValidationResults'
import { formatBRL } from '@/lib/utils'
import { downloadDocumentReport } from '@/services/api'

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const docId = id ? +id : 0
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  const scoreQuery = useDocumentScore(docId)
  const resultsQuery = useValidationResults(docId)

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true)
    try {
      await downloadDocumentReport(docId)
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Erro ao gerar PDF')
    } finally {
      setDownloadingPdf(false)
    }
  }

  const score = scoreQuery.data
  const results = resultsQuery.data?.results ?? []

  return (
    <div className="flex flex-col h-full">
      <TopBar title={`Documento #${docId}`}>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="flex items-center gap-2"
          >
            {downloadingPdf ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            {downloadingPdf ? 'Gerando...' : 'Baixar PDF'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            className="flex items-center gap-2"
          >
            <ArrowLeft size={18} />
            Voltar
          </Button>
        </div>
      </TopBar>

      <div className="flex-1 overflow-y-auto p-8 space-y-8">
        {scoreQuery.isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-32" />
            <Skeleton className="h-96" />
          </div>
        ) : !score ? (
          <Card>
            <CardContent className="py-8 text-center text-slate-500">
              Documento não encontrado
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Score Section */}
            <div className="grid grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Score de Risco</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScoreGauge score={score.document_score} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Exposição Financeira</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm text-slate-600">Exposição Total Estimada</p>
                    <p className="text-3xl font-bold text-red-600">
                      {formatBRL(score.total_exposure)}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                    <div>
                      <p className="text-sm text-slate-600">Regras Falhadas</p>
                      <p className="text-2xl font-semibold">{score.rules_failed}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-600">Regras Aprovadas</p>
                      <p className="text-2xl font-semibold text-green-600">{score.rules_passed}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Validation Results */}
            <Card>
              <CardHeader>
                <CardTitle>Resultados de Validação ({score.total_rules} regras)</CardTitle>
              </CardHeader>
              <CardContent>
                <ValidationTable
                  results={results}
                  loading={resultsQuery.isLoading}
                />
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  )
}
