import { useCallback, useEffect, useRef, useState } from 'react'
import { evaluateHypercare, getHypercareRules, requestHypercare } from '@/api/client'
import type { HypercareEvidence, HypercareEvidenceClip, HypercareManualRequest } from '@/api/types'
import EvidenceCard from '@/components/hypercare/EvidenceCard'
import RuleBuilder from '@/components/hypercare/RuleBuilder'
import RuleCard from '@/components/hypercare/RuleCard'
import {
  HypercareRulesProvider,
  useHypercareRules,
} from '@/state/hypercareRules'
import { useRole } from '@/state/role'

type Tab = 'rules' | 'evidence' | 'request'

function HypercareInner() {
  const [tab, setTab] = useState<Tab>('rules')
  const { rules, toggleRule, setSeed } = useHypercareRules()
  const { role } = useRole()

  const [evidence, setEvidence] = useState<HypercareEvidence[]>([])
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)

  const [requestLoading, setRequestLoading] = useState(false)
  const [requestResult, setRequestResult] = useState<HypercareEvidence | null>(null)

  const seedLoadedRef = useRef(false)

  useEffect(() => {
    if (seedLoadedRef.current) return
    seedLoadedRef.current = true
    getHypercareRules()
      .then(setSeed)
      .catch(() => {/* seed failure is silent — fixture fallback active */})
  }, [setSeed])

  const loadEvidence = useCallback(async () => {
    setEvidenceLoading(true)
    setEvidenceError(null)
    try {
      const data = await evaluateHypercare(rules, role)
      setEvidence(data)
    } catch {
      setEvidenceError('Не удалось загрузить доказательства')
    } finally {
      setEvidenceLoading(false)
    }
  }, [rules, role])

  useEffect(() => {
    if (tab === 'evidence') {
      loadEvidence()
    }
  }, [tab, loadEvidence])

  async function handleRequest(req: HypercareManualRequest) {
    setRequestLoading(true)
    setRequestResult(null)
    try {
      const result = await requestHypercare(req)
      setRequestResult(result)
    } catch {
      /* request error — result stays null */
    } finally {
      setRequestLoading(false)
    }
  }

  function handleOpenClip(clip: HypercareEvidenceClip) {
    if (clip.url) {
      window.open(clip.url, '_blank', 'noopener')
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-ink">Гиперопека</h1>
        <span className="text-sm text-muted">{rules.filter((r) => r.enabled).length} правил активно</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {([['rules', 'Правила'], ['evidence', 'Доказательства'], ['request', 'Запрос']] as const).map(
          ([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={[
                'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
                tab === key
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted hover:text-ink',
              ].join(' ')}
              aria-selected={tab === key}
            >
              {label}
            </button>
          ),
        )}
      </div>

      {/* Rules tab */}
      {tab === 'rules' && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {rules.map((rule) => (
            <RuleCard key={rule.id} rule={rule} onToggle={toggleRule} />
          ))}
          {rules.length === 0 && (
            <p className="text-sm text-muted col-span-full">Правила загружаются…</p>
          )}
        </div>
      )}

      {/* Evidence tab */}
      {tab === 'evidence' && (
        <div className="flex flex-col gap-3">
          <div className="flex gap-2 items-center">
            <button
              onClick={loadEvidence}
              disabled={evidenceLoading}
              className="rounded border border-border px-3 py-1.5 text-sm font-medium text-ink hover:bg-bg disabled:opacity-50"
            >
              {evidenceLoading ? 'Загрузка…' : '↻ Обновить'}
            </button>
            {evidenceError && <span className="text-sm text-red-600">{evidenceError}</span>}
          </div>
          {evidence.map((ev) => (
            <EvidenceCard key={ev.id} evidence={ev} onOpenClip={handleOpenClip} />
          ))}
          {!evidenceLoading && evidence.length === 0 && !evidenceError && (
            <p className="text-sm text-muted">Нет доказательств по активным правилам</p>
          )}
        </div>
      )}

      {/* Manual request tab */}
      {tab === 'request' && (
        <div className="max-w-md flex flex-col gap-4">
          <RuleBuilder onSubmit={handleRequest} loading={requestLoading} />
          {requestResult && (
            <EvidenceCard evidence={requestResult} onOpenClip={handleOpenClip} />
          )}
        </div>
      )}
    </div>
  )
}

export default function Hypercare() {
  return (
    <HypercareRulesProvider>
      <HypercareInner />
    </HypercareRulesProvider>
  )
}
