import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { Severity, RuleLogSeverity } from '@/types/api'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBRL(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

export function formatDate(date: string): string {
  return new Intl.DateTimeFormat('pt-BR').format(new Date(date))
}

export function truncateChave(chave: string): string {
  if (!chave || chave.length <= 20) return chave
  return `${chave.slice(0, 8)}…${chave.slice(-8)}`
}

export function scoreColorClass(score: number): string {
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

export function scoreBgClass(score: number): string {
  if (score >= 80) return 'bg-green-50 border-green-200'
  if (score >= 60) return 'bg-yellow-50 border-yellow-200'
  return 'bg-red-50 border-red-200'
}

export const SEVERITY_STYLES: Record<Severity | RuleLogSeverity, string> = {
  CRITICAL: 'bg-red-100 text-red-800 border-red-200',
  HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
  MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  LOW: 'bg-green-100 text-green-800 border-green-200',
  WARNING: 'bg-orange-100 text-orange-800 border-orange-200',
  INFO: 'bg-blue-100 text-blue-800 border-blue-200',
  INFORMATIVE: 'bg-gray-100 text-gray-600 border-gray-200',
}

export const SEVERITY_COLOR: Record<Severity | RuleLogSeverity, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#ea580c',
  MEDIUM: '#ca8a04',
  LOW: '#16a34a',
  WARNING: '#ea580c',
  INFO: '#3b82f6',
  INFORMATIVE: '#9ca3af',
}

export function getSeverityLabel(severity: string | null | undefined): string {
  if (!severity) return 'N/A'
  const labels: Record<string, string> = {
    CRITICAL: 'Crítico',
    HIGH: 'Alto',
    MEDIUM: 'Médio',
    LOW: 'Baixo',
    WARNING: 'Aviso',
    INFO: 'Info',
    INFORMATIVE: 'Informativo',
  }
  return labels[severity] || severity
}

export function getCurrentYearMonth(): [number, number] {
  const now = new Date()
  return [now.getFullYear(), now.getMonth() + 1]
}

export function formatYearMonth(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`
}
