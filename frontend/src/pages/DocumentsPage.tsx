import { TopBar } from '@/components/layout/TopBar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DocumentsTable } from '@/components/documents/DocumentsTable'
import { EmptyState } from '@/components/documents/EmptyState'
import { useDocuments } from '@/hooks/useDocuments'

export function DocumentsPage() {
  const { data, isLoading } = useDocuments()
  const documents = data?.documents ?? []

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Documentos" />
      <div className="flex-1 overflow-y-auto p-8">
        <Card>
          <CardHeader>
            <CardTitle>Lista de Documentos Fiscais</CardTitle>
          </CardHeader>
          <CardContent>
            {documents.length === 0 && !isLoading ? (
              <EmptyState />
            ) : (
              <DocumentsTable documents={documents} loading={isLoading} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
