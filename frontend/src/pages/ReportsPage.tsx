import { useState } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, FileText, BarChart3 } from 'lucide-react';

export function ReportsPage() {
  const [selectedReport, setSelectedReport] = useState<string | null>(null);

  const reports = [
    {
      id: 'executive',
      title: 'Relatório Executivo',
      description: 'Resumo das inconsistências e recomendações prioritárias',
      icon: BarChart3,
    },
    {
      id: 'detailed',
      title: 'Relatório Detalhado',
      description: 'Análise completa com todos os achados e evidências',
      icon: FileText,
    },
  ];

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reports.map((report) => {
            const Icon = report.icon;
            return (
              <Card
                key={report.id}
                className="p-6 cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => setSelectedReport(report.id)}
              >
                <div className="flex items-start gap-4">
                  <Icon className="w-8 h-8 text-blue-600 mt-1" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg">{report.title}</h3>
                    <p className="text-gray-600 text-sm mt-2">{report.description}</p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        <Card className="p-6">
          <h3 className="font-semibold text-lg mb-6">Exportação</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Período</label>
              <select className="w-full px-3 py-2 border rounded">
                <option>Últimos 30 dias</option>
                <option>Últimos 90 dias</option>
                <option>Este ano</option>
                <option>Período customizado</option>
              </select>
            </div>
            <div className="flex gap-3">
              <Button className="flex items-center gap-2">
                <Download className="w-4 h-4" />
                Baixar PDF
              </Button>
              <Button variant="outline" className="flex items-center gap-2">
                <Download className="w-4 h-4" />
                Exportar Excel
              </Button>
            </div>
          </div>
        </Card>

        {selectedReport && (
          <Card className="p-6 bg-blue-50">
            <h4 className="font-semibold mb-3">
              {reports.find(r => r.id === selectedReport)?.title}
            </h4>
            <p className="text-gray-700 text-sm">
              Este relatório será gerado com base nos últimos documentos processados.
              Clique em "Baixar PDF" para gerar o documento.
            </p>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
