import { useState } from 'react'
import { Upload } from 'lucide-react'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DocumentsTable } from '@/components/documents/DocumentsTable'
import { EmptyState } from '@/components/documents/EmptyState'
import { UploadZone } from '@/components/documents/UploadZone'
import { useDocuments } from '@/hooks/useDocuments'

export function DocumentsPage() {
  const [showUpload, setShowUpload] = useState(false)
  const { data, isLoading, refetch } = useDocuments()
  const documents = data?.documents ?? []

  const handleUploadComplete = () => {
    setShowUpload(false)
    refetch()
  }

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Documentos">
        <Button size="sm" onClick={() => setShowUpload((v) => !v)}>
          <Upload size={16} className="mr-2" />
          Importar Documentos
        </Button>
      </TopBar>

      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {showUpload && (
          <Card>
            <CardHeader>
              <CardTitle>Importar Arquivos Fiscais</CardTitle>
            </CardHeader>
            <CardContent>
              <UploadZone onUploadComplete={handleUploadComplete} />
            </CardContent>
          </Card>
        )}

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
