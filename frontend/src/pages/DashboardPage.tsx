import { useState } from 'react'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { KpiCard } from '@/components/dashboard/KpiCard'
import { PeriodSelector } from '@/components/dashboard/PeriodSelector'
import { AlertsTable } from '@/components/dashboard/AlertsTable'
import { SeverityChart } from '@/components/dashboard/SeverityChart'
import { TopFailedRules } from '@/components/dashboard/TopFailedRules'
import { usePeriodScore } from '@/hooks/usePeriodScore'
import { useAlertQueue } from '@/hooks/useAlertQueue'
import { formatBRL, getCurrentYearMonth } from '@/lib/utils'

export function DashboardPage() {
  const [year, month] = getCurrentYearMonth()
  const [selectedYear, setSelectedYear] = useState(year)
  const [selectedMonth, setSelectedMonth] = useState(month)

  const periodQuery = usePeriodScore(selectedYear, selectedMonth)
  const alertsQuery = useAlertQueue(10)

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Dashboard" >
        <PeriodSelector
          year={selectedYear}
          month={selectedMonth}
          onChange={(y, m) => {
            setSelectedYear(y)
            setSelectedMonth(m)
          }}
        />
      </TopBar>

      <div className="flex-1 overflow-y-auto p-8 space-y-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4">
          <KpiCard
            title="Score do Período"
            value={periodQuery.data?.period_score ?? 0}
            variant="score"
            score={periodQuery.data?.period_score}
            loading={periodQuery.isLoading}
          />
          <KpiCard
            title="Exposição Total"
            value={periodQuery.data ? formatBRL(periodQuery.data.total_exposure) : 'R$ 0,00'}
            variant="currency"
            loading={periodQuery.isLoading}
          />
          <KpiCard
            title="Documentos Críticos"
            value={periodQuery.data?.critical_documents ?? 0}
            variant="count"
            loading={periodQuery.isLoading}
          />
          <KpiCard
            title="Documentos Processados"
            value={periodQuery.data?.documents_processed ?? 0}
            variant="count"
            loading={periodQuery.isLoading}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-3 gap-6">
          {/* Alerts Table */}
          <div className="col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Alertas Prioritários (Top 10)</CardTitle>
              </CardHeader>
              <CardContent>
                <AlertsTable
                  alerts={alertsQuery.data?.alerts ?? []}
                  loading={alertsQuery.isLoading}
                />
              </CardContent>
            </Card>
          </div>

          {/* Severity Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Distribuição por Severidade</CardTitle>
            </CardHeader>
            <CardContent>
              <SeverityChart
                data={periodQuery.data?.alerts_by_severity ?? { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 }}
                loading={periodQuery.isLoading}
              />
            </CardContent>
          </Card>
        </div>

        {/* Top Failed Rules */}
        <Card>
          <CardHeader>
            <CardTitle>Top 3 Regras Falhadas</CardTitle>
          </CardHeader>
          <CardContent>
            <TopFailedRules rules={periodQuery.data?.top_3_rules ?? []} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
