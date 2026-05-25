// ── Shared ──────────────────────────────────────────────────────────────

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIVE'
export type RuleLogSeverity = 'CRITICAL' | 'WARNING' | 'INFO'

// ── GET /api/v1/alerts/priority-queue ────────────────────────────────────────

export interface Alert {
  rule_id: string
  rule_version: string
  severity: Severity
  fiscal_document_id: number
  document_chave: string
  document_value: number
  exposure: number
  priority_score: number
  message: string
  created_at: string | null
}

export interface AlertQueueResponse {
  alerts: Alert[]
  total: number
}

// ── GET /api/v1/periods/{year}/{month}/score ─────────────────────────────────

export interface TopRule {
  rule_id: string
  failures: number
}

export interface AlertsBySeverity {
  CRITICAL: number
  HIGH: number
  MEDIUM: number
  LOW: number
}

export interface PeriodScoreResponse {
  period: string
  documents_processed: number
  critical_documents: number
  period_score: number
  total_exposure: number
  top_3_rules: TopRule[]
  alerts_by_severity: AlertsBySeverity
}

// ── GET /api/v1/documents/{id}/score ─────────────────────────────────────────

export interface AlertsBySeverityFull extends AlertsBySeverity {
  INFORMATIVE: number
}

export interface DocumentScoreResponse {
  fiscal_document_id: number
  alerts_by_severity: AlertsBySeverityFull
  total_exposure: number
  document_score: number
  rules_failed: number
  rules_passed: number
  total_rules: number
}

// ── GET /api/v1/documents/{id}/validation-results ────────────────────────────

export interface ValidationResult {
  rule_id: string
  rule_version: string
  passed: boolean
  severity: RuleLogSeverity | null
  message: string | null
  triggered_by: string
  created_at: string | null
}

export interface ValidationResultsResponse {
  document_id: number
  results: ValidationResult[]
}

// ── GET /api/v1/documents ─────────────────────────────────────────────────────

export interface Document {
  document_id?: number
  chave_acesso?: string
  numero_nf?: string
  emitente_nome?: string
  data_emissao?: string
  status_nfe?: 'autorizado' | 'cancelado' | 'denegado'
  document_score?: number
}

export interface DocumentsResponse {
  documents: Document[]
}
