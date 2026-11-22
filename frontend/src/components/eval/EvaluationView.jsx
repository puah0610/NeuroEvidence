import { useMemo } from 'react'
import {
  Activity,
  ArrowLeft,
  Clock3,
  FlaskConical,
  MessageSquareText,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'

export default function EvaluationView({ summary, loading = false, onRefresh, onBackToChat }) {
  const cards = useMemo(
    () => [
      ['Recorded traces', summary?.total_traces ?? 0, Activity, 'All local experiments'],
      [
        'Average score',
        summary?.average_evidence_score != null
          ? `${Math.round(summary.average_evidence_score * 100)}%`
          : '—',
        ShieldCheck,
        'Verified mode only',
      ],
      [
        'Average latency',
        summary?.average_latency_ms != null ? `${Math.round(summary.average_latency_ms)} ms` : '—',
        Clock3,
        'Across all modes',
      ],
      [
        'Estimated API cost',
        summary?.total_estimated_cost_usd
          ? `$${summary.total_estimated_cost_usd.toFixed(4)}`
          : '$0.0000',
        FlaskConical,
        `${(summary?.total_input_tokens ?? 0) + (summary?.total_output_tokens ?? 0)} tokens`,
      ],
      [
        'Feedback entries',
        summary?.feedback_count ?? 0,
        MessageSquareText,
        summary?.helpful_rate != null
          ? `${Math.round(summary.helpful_rate * 100)}% helpful`
          : 'No ratings yet',
      ],
    ],
    [summary]
  )

  return (
    <div className="min-h-[calc(100vh-65px)] overflow-y-auto px-6 py-8 lg:px-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-ocean">Local Research Dashboard</p>
            <h1 className="mt-1 font-display text-3xl font-bold text-ink">Evaluation Overview</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
              Descriptive metrics calculated from local experiment traces. Thesis benchmarks should be validated against the locked baseline test suite.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {onRefresh && (
              <button
                type="button"
                onClick={onRefresh}
                disabled={loading}
                className="flex items-center gap-1.5 rounded-xl border border-neutral-200 bg-white px-3.5 py-2 text-xs font-semibold text-neutral-700 shadow-2xs hover:bg-neutral-50 transition disabled:opacity-50"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                <span>{loading ? 'Refreshing...' : 'Refresh'}</span>
              </button>
            )}
            {onBackToChat && (
              <button
                type="button"
                onClick={onBackToChat}
                className="flex items-center gap-1.5 rounded-xl bg-ink px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-ocean transition"
              >
                <ArrowLeft size={14} />
                <span>Back to Chat</span>
              </button>
            )}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {cards.map(([label, value, Icon, note]) => (
            <div key={label} className="rounded-2xl border border-neutral-200/80 bg-white p-5 shadow-xs">
              <div className="mb-4 grid h-10 w-10 place-items-center rounded-xl bg-mint text-ocean">
                <Icon size={20} />
              </div>
              <div className="font-display text-3xl font-bold text-ink">{value}</div>
              <div className="mt-1 text-sm font-semibold text-ink/80">{label}</div>
              <div className="mt-1 text-xs text-neutral-400">{note}</div>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Breakdown
            title="Runs by execution mode"
            data={summary?.by_mode}
            labels={{
              rag_verified: 'Cloud RAG (Verified)',
              baseline: 'Cloud Baseline (Zero-Shot)',
              ollama_rag: 'Local RAG (Ollama)',
              ollama_baseline: 'Local Baseline (Ollama)',
            }}
          />
          <Breakdown
            title="Safety and scope routing"
            data={summary?.by_intent}
            labels={{
              educational_in_scope: 'Educational, in scope',
              out_of_scope: 'Out of scope',
              personal_medical_advice: 'Personal medical advice',
              emergency: 'Emergency',
            }}
          />
        </div>

        <div className="mt-6 rounded-2xl border border-ocean/15 bg-mint/40 p-6">
          <div className="flex gap-4">
            <FlaskConical className="shrink-0 text-ocean mt-0.5" />
            <div>
              <h2 className="font-display text-lg font-bold text-ink">3-Layer Triad Verification Protocol</h2>
              <p className="mt-1.5 text-sm leading-6 text-neutral-600">
                Verified clinical responses balance Foundational Knowledge (Layer 1), Clinical Practice Guidelines (Layer 2), and Empirical Trial Remission/Safety Evidence (Layer 3) with claim-level NLI entailment.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Breakdown({ title, data = {}, labels }) {
  const entries = Object.entries(data || {})
  const total = Math.max(1, entries.reduce((sum, [, value]) => sum + value, 0))

  return (
    <div className="rounded-2xl border border-neutral-200/80 bg-white p-6 shadow-xs">
      <h2 className="mb-5 font-display text-lg font-bold text-ink">{title}</h2>
      {entries.length ? (
        <div className="space-y-4">
          {entries.map(([key, value]) => (
            <div key={key}>
              <div className="mb-1.5 flex justify-between text-xs">
                <span className="font-medium text-neutral-700">{labels[key] || key}</span>
                <span className="font-semibold text-ink">{value}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-neutral-100">
                <div
                  className="h-full rounded-full bg-ocean transition-all duration-500"
                  style={{ width: `${(value / total) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid min-h-28 place-items-center rounded-xl border border-dashed border-neutral-200 text-sm text-neutral-400">
          No traces recorded yet
        </div>
      )}
    </div>
  )
}
