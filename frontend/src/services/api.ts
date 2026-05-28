import axios from 'axios'
import type {
  AlertQueueResponse,
  AlertsListResponse,
  PeriodScoreResponse,
  DocumentScoreResponse,
  ValidationResultsResponse,
  DocumentsResponse,
  UploadResponse,
} from '@/types/api'
import type { TokenResponse } from '@/types/auth'

const TOKEN_KEY = 'fiscalai_token'
const REFRESH_TOKEN_KEY = 'fiscalai_refresh'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: adiciona Bearer token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: trata 401 com refresh token
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
        if (!refreshToken) {
          // Sem refresh token, redirecionar para login
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(REFRESH_TOKEN_KEY)
          window.location.href = '/login'
          return Promise.reject(error)
        }

        // Tentar refresh
        const refreshResponse = await axios.post<TokenResponse>(
          '/api/v1/auth/refresh',
          { refresh_token: refreshToken },
          { baseURL: '/' }
        )

        const { access_token, refresh_token } = refreshResponse.data
        localStorage.setItem(TOKEN_KEY, access_token)
        localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)

        // Retry original request com novo token
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return client(originalRequest)
      } catch (refreshError) {
        // Refresh falhou, limpar e redirecionar
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// ── Alerts ────────────────────────────────────────────────────────────────────

export const fetchAlertQueue = (limit = 10): Promise<AlertQueueResponse> =>
  client
    .get<AlertQueueResponse>('/alerts/priority-queue', {
      params: { limit },
    })
    .then((r) => r.data)

export interface AlertsFilter {
  severity?: string[]
  rule_id?: string
  fiscal_year?: number
  fiscal_month?: number
  min_exposure?: number
  max_exposure?: number
  page?: number
  page_size?: number
}

export const fetchAlerts = (filter: AlertsFilter = {}): Promise<AlertsListResponse> =>
  client
    .get<AlertsListResponse>('/alerts', { params: filter })
    .then((r) => r.data)

// ── Period Score ──────────────────────────────────────────────────────────────

export const fetchPeriodScore = (
  year: number,
  month: number
): Promise<PeriodScoreResponse> =>
  client
    .get<PeriodScoreResponse>(`/periods/${year}/${month}/score`)
    .then((r) => r.data)

// ── Document Score ────────────────────────────────────────────────────────────

export const fetchDocumentScore = (id: number): Promise<DocumentScoreResponse> =>
  client.get<DocumentScoreResponse>(`/documents/${id}/score`).then((r) => r.data)

// ── Validation Results ────────────────────────────────────────────────────────

export const fetchValidationResults = (
  id: number
): Promise<ValidationResultsResponse> =>
  client
    .get<ValidationResultsResponse>(`/documents/${id}/validation-results`)
    .then((r) => r.data)

// ── Documents List ────────────────────────────────────────────────────────────

export const fetchDocuments = (): Promise<DocumentsResponse> =>
  client.get<DocumentsResponse>('/documents').then((r) => r.data)

// ── Upload ────────────────────────────────────────────────────────────────────

export const uploadFiles = (
  files: File[],
  onProgress?: (percent: number) => void
): Promise<UploadResponse> => {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))

  return client
    .post<UploadResponse>('/uploads', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded * 100) / event.total))
        }
      },
    })
    .then((r) => r.data)
}

// ── Trend ────────────────────────────────────────────────────────────────────

export interface PeriodTrendPoint {
  period: string
  period_score: number
  total_exposure: number
  documents_processed: number
  critical_documents: number
}

export const fetchPeriodTrend = (months = 12): Promise<PeriodTrendPoint[]> =>
  client.get<PeriodTrendPoint[]>('/periods/trend', { params: { months } }).then((r) => r.data)

// ── Reports ───────────────────────────────────────────────────────────────────

export const downloadReport = async (
  year: number,
  month: number,
  format: 'pdf' | 'excel'
): Promise<void> => {
  const endpoint = `/reports/period/${year}/${month}/${format}`
  const mimeType =
    format === 'pdf'
      ? 'application/pdf'
      : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  const ext = format === 'pdf' ? 'pdf' : 'xlsx'

  const token = localStorage.getItem('fiscalai_token')
  const response = await fetch(`/api/v1${endpoint}`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? `Erro ${response.status}`)
  }

  const blob = await response.blob()
  const url = URL.createObjectURL(new Blob([blob], { type: mimeType }))
  const a = document.createElement('a')
  a.href = url
  a.download = `fiscalai-${year}-${String(month).padStart(2, '0')}.${ext}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export const downloadDocumentReport = async (documentId: number): Promise<void> => {
  const token = localStorage.getItem('fiscalai_token')
  const response = await fetch(`/api/v1/reports/document/${documentId}/pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? `Erro ${response.status}`)
  }

  const blob = await response.blob()
  const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `fiscalai-documento-${documentId}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ── Job Status ────────────────────────────────────────────────────────────────

export interface JobStatusResponse {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  document_id?: number
  original_filename?: string
  document_type?: string
  error?: string
}

export const fetchJobStatus = (jobId: string): Promise<JobStatusResponse> =>
  client.get<JobStatusResponse>(`/jobs/${jobId}`).then((r) => r.data)
