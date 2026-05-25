import { Badge } from '@/components/ui/badge'
import type { TopRule } from '@/types/api'

interface TopFailedRulesProps {
  rules: TopRule[]
}

export function TopFailedRules({ rules }: TopFailedRulesProps) {
  if (!rules || rules.length === 0) {
    return <p className="text-center text-slate-500 py-4">Sem regras falhadas</p>
  }

  return (
    <ol className="space-y-2">
      {rules.map((rule, idx) => (
        <li key={rule.rule_id} className="flex items-center justify-between rounded-lg border p-3">
          <div className="flex items-center gap-3">
            <Badge variant="secondary" className="font-semibold">
              {idx + 1}
            </Badge>
            <span className="font-mono font-semibold">{rule.rule_id}</span>
          </div>
          <Badge variant="outline">{rule.failures} falha(s)</Badge>
        </li>
      ))}
    </ol>
  )
}
