import { useCallback, useState } from 'react'
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { uploadFiles } from '@/services/api'
import { useJobPolling } from '@/hooks/useJobPolling'
import type { UploadFileResult } from '@/types/api'

interface UploadZoneProps {
  onUploadComplete?: () => void
}

interface FileUploadState {
  file: File
  progress: number
  status: 'pending' | 'uploading' | 'done' | 'error'
  result?: UploadFileResult
  jobId?: string
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function UploadZone({ onUploadComplete }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [files, setFiles] = useState<FileUploadState[]>([])
  const [isUploading, setIsUploading] = useState(false)

  // Track which job we're polling
  const jobsInProgress = files
    .filter((f) => f.status === 'uploading' && f.jobId)
    .map((f) => f.jobId)
  const currentJobId = jobsInProgress[0] ?? null

  useJobPolling(currentJobId, {
    interval: 2000,
    onComplete: (jobData) => {
      toast.success(`Documento processado: ${jobData.original_filename}`)

      // Update file status to done
      setFiles((prev) =>
        prev.map((f) =>
          f.jobId === jobData.job_id
            ? {
                ...f,
                status: 'done',
                progress: 100,
                result: {
                  filename: jobData.original_filename ?? f.file.name,
                  status: 'accepted',
                },
              }
            : f
        )
      )

      // Trigger refetch if all jobs done
      setTimeout(() => {
        const stillProcessing = files.some((f) => f.status === 'uploading')
        if (!stillProcessing) {
          onUploadComplete?.()
        }
      }, 500)
    },
    onError: (error) => {
      console.error('Polling error:', error)
      // Don't toast every error — will retry automatically
    },
  })

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const arr = Array.from(incoming)
    setFiles((prev) => [
      ...prev,
      ...arr.map((f) => ({ file: f, progress: 0, status: 'pending' as const })),
    ])
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files)
    },
    [addFiles]
  )

  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(e.target.files)
    e.target.value = ''
  }

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleUpload = async () => {
    const pending = files.filter((f) => f.status === 'pending')
    if (pending.length === 0) return

    setIsUploading(true)

    // Mark all pending as uploading
    setFiles((prev) =>
      prev.map((f) => (f.status === 'pending' ? { ...f, status: 'uploading' } : f))
    )

    try {
      const response = await uploadFiles(
        pending.map((f) => f.file),
        (percent) => {
          setFiles((prev) =>
            prev.map((f) =>
              f.status === 'uploading' ? { ...f, progress: percent } : f
            )
          )
        }
      )

      // Map results back to files with job IDs
      setFiles((prev) => {
        const uploading = prev.filter((f) => f.status === 'uploading')
        const rest = prev.filter((f) => f.status !== 'uploading')
        const updated = uploading.map((f, i) => {
          const result = response.results[i]
          if (result?.status === 'accepted' && result.job_id) {
            toast.info(`Processando: ${f.file.name}...`)
            return {
              ...f,
              progress: 100,
              status: 'uploading' as const, // Stay uploading until polling completes
              result,
              jobId: result.job_id,
            }
          } else if (result?.status === 'duplicate') {
            toast.warning(`Arquivo duplicado: ${f.file.name}`)
            return {
              ...f,
              progress: 100,
              status: 'done' as const,
              result,
            }
          } else {
            toast.error(`Erro ao enviar ${f.file.name}: ${result?.reason}`)
            return {
              ...f,
              progress: 0,
              status: 'error' as const,
              result: result ?? {
                filename: f.file.name,
                status: 'error',
                reason: 'Erro desconhecido',
              },
            }
          }
        })
        return [...rest, ...updated]
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload falhou'
      toast.error(message)

      setFiles((prev) =>
        prev.map((f) =>
          f.status === 'uploading'
            ? {
                ...f,
                status: 'error',
                result: { filename: f.file.name, status: 'error', reason: message },
              }
            : f
        )
      )
    } finally {
      setIsUploading(false)
    }
  }

  const hasPending = files.some((f) => f.status === 'pending')

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDrop={onDrop}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
        }`}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <Upload className="mx-auto mb-3 text-slate-400" size={36} />
        <p className="text-sm font-medium text-slate-700">
          Arraste arquivos aqui ou <span className="text-blue-600">clique para selecionar</span>
        </p>
        <p className="mt-1 text-xs text-slate-500">
          SPED EFD (.txt), NF-e / CT-e (.xml) — até 2 GB por arquivo
        </p>
        <input
          id="file-input"
          type="file"
          multiple
          accept=".txt,.xml"
          className="hidden"
          onChange={onFileInput}
        />
      </div>

      {/* File list */}
      {files.length > 0 && (
        <ul className="space-y-2">
          {files.map((item, idx) => (
            <li
              key={idx}
              className="flex items-center gap-3 rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
            >
              <FileText size={16} className="shrink-0 text-slate-400" />
              <span className="flex-1 truncate font-medium text-slate-700">
                {item.file.name}
              </span>
              <span className="shrink-0 text-slate-400">{formatBytes(item.file.size)}</span>

              {item.status === 'uploading' && item.progress < 100 && (
                <span className="flex items-center gap-1 text-blue-600">
                  <Loader2 size={14} className="animate-spin" />
                  {item.progress}%
                </span>
              )}
              {item.status === 'uploading' && item.progress === 100 && (
                <span className="flex items-center gap-1 text-amber-600">
                  <Loader2 size={14} className="animate-spin" />
                  Processando...
                </span>
              )}
              {item.status === 'done' && item.result?.status === 'accepted' && (
                <CheckCircle size={16} className="text-green-500" />
              )}
              {item.status === 'done' && item.result?.status === 'duplicate' && (
                <span className="text-xs text-amber-600">duplicado</span>
              )}
              {item.status === 'error' && (
                <span className="flex items-center gap-1 text-red-500">
                  <AlertCircle size={14} />
                  <span className="text-xs">{item.result?.reason ?? 'erro'}</span>
                </span>
              )}
              {item.status === 'pending' && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    removeFile(idx)
                  }}
                  className="text-slate-300 hover:text-red-400"
                >
                  <X size={14} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Actions */}
      {hasPending && (
        <div className="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setFiles((prev) => prev.filter((f) => f.status !== 'pending'))}
          >
            Limpar
          </Button>
          <Button size="sm" onClick={handleUpload} disabled={isUploading}>
            {isUploading ? (
              <>
                <Loader2 size={14} className="mr-2 animate-spin" />
                Enviando...
              </>
            ) : (
              `Enviar ${files.filter((f) => f.status === 'pending').length} arquivo(s)`
            )}
          </Button>
        </div>
      )}
    </div>
  )
}
