import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  CircleHelp,
  ExternalLink,
  FileCheck2,
  FlaskConical,
  Info,
  Layers,
  ShieldCheck,
  XCircle,
} from 'lucide-react'

export default function EvidenceInspector({
  result,
  onBackToBoard,
}) {
  if (!result) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center text-neutral-400">
        <FileCheck2 size={36} className="text-neutral-300 mb-3" />
        <p className="text-sm font-medium">No query evidence to inspect yet.</p>
        <p className="text-xs text-neutral-400 mt-1 max-w-sm">
          Run a clinical question from the right copilot or select one from the Knowledge Board.
        </p>
        <button
          onClick={onBackToBoard}
          className="mt-4 rounded-xl bg-ink px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-ocean transition"
        >
          Return to Knowledge Board
        </button>
      </div>
    )
  }

  const score = result.evidence_score != null ? Math.round(result.evidence_score * 100) : null
  const passed = result.evidence_score != null && result.evidence_score >= (result.evidence_threshold || 0.6)

  const citations = result.citations || []
  const l1Count = citations.filter((c) => (c.layer || 1) === 1).length
  const l2Count = citations.filter((c) => c.layer === 2).length
  const l3Count = citations.filter((c) => c.layer === 3).length

  return (
    <div className="h-full overflow-y-auto p-6 lg:p-8">
      {/* Top Navigation & Status Bar */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-neutral-200/60 pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToBoard}
            className="flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 shadow-2xs transition hover:border-neutral-300 hover:bg-neutral-50"
          >
            <ArrowLeft size={14} />
            <span>Knowledge Board</span>
          </button>
          <div className="h-4 w-[1px] bg-neutral-200" />
          <div className="flex items-center gap-2">
            <span className="font-display text-sm font-bold text-ink">Active Evidence Inspector</span>
            {result.demo_mode && (
              <span className="rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                Demo
              </span>
            )}
          </div>
        </div>

        {/* Evidence Score & Layer Badges */}
        <div className="flex flex-wrap items-center gap-2">
          {score != null && (
            <div
              className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-bold ${
                passed
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                  : 'border-amber-200 bg-amber-50 text-amber-800'
              }`}
            >
              <CheckCircle2 size={13} />
              <span>{score}% Grounded</span>
            </div>
          )}

          <div className="flex items-center gap-1 text-[11px] font-medium text-neutral-500">
            <span className="rounded bg-indigo-50 border border-indigo-200 px-1.5 py-0.5 text-indigo-800 font-bold">
              L1: {l1Count}
            </span>
            <span className="rounded bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 text-emerald-800 font-bold">
              L2: {l2Count}
            </span>
            <span className="rounded bg-purple-50 border border-purple-200 px-1.5 py-0.5 text-purple-800 font-bold">
              L3: {l3Count}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-6 max-w-5xl">
        {/* Drug-Drug Interaction Card (if active) */}
        {result.ddi_report && <DDIAlertCard report={result.ddi_report} />}

        {/* Warnings & Scope */}
        {result.warnings?.length > 0 && (
          <div className="rounded-2xl border border-amber-200/80 bg-amber-50/70 p-4 text-xs text-amber-900">
            <div className="flex items-center gap-2 font-bold mb-1">
              <AlertTriangle size={15} className="text-amber-700" />
              <span>Clinical Guidance Notice</span>
            </div>
            {result.warnings.map((w, idx) => (
              <p key={idx} className="text-amber-800/80 leading-relaxed">
                {w}
              </p>
            ))}
          </div>
        )}

        {/* Bounded Answer Revision Trace */}
        {result.original_answer && (
          <div className="rounded-2xl border border-sky-200/80 bg-sky-50/50 p-4 text-xs shadow-2xs">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2 font-bold text-sky-950">
                <ShieldCheck size={16} className="text-sky-700" />
                <span>Bounded Answer Revision Audit</span>
              </div>
              <span className="rounded-full bg-sky-100 border border-sky-200 px-2 py-0.5 text-[10px] font-bold text-sky-800">
                Draft Revised via NLI Feedback
              </span>
            </div>
            <p className="text-sky-900/80 leading-relaxed mb-3">
              The initial model draft contained unsupported claims or misattributed citations. The pipeline performed targeted secondary retrieval and updated the inline citations and claims to match the verified evidence.
            </p>
            <details className="text-xs">
              <summary className="cursor-pointer font-semibold text-sky-900 hover:text-sky-700 select-none">
                Inspect Initial Pre-Revision Draft (Research Trace) ▸
              </summary>
              <div className="mt-2.5 rounded-xl border border-neutral-200 bg-white p-3 font-mono text-[11px] text-neutral-600 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                {result.original_answer}
              </div>
            </details>
          </div>
        )}

        {/* Selective Query Decomposition Audit */}
        {result.subqueries && result.subqueries.length > 1 && (
          <div className="rounded-2xl border border-violet-200/80 bg-violet-50/50 p-4 text-xs shadow-2xs">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 font-bold text-violet-950">
                <Layers size={16} className="text-violet-700" />
                <span>Selective Query Decomposition Audit ({result.subqueries.length} Subqueries)</span>
              </div>
              <span className="rounded-full bg-violet-100 border border-violet-200 px-2 py-0.5 text-[10px] font-bold text-violet-800">
                Triad-Aligned Partitioning
              </span>
            </div>
            <p className="text-violet-900/80 leading-relaxed mb-3">
              The compound inquiry was decomposed into distinct subqueries preserving clinical constraints, retrieved across Triad layers, and deduplicated:
            </p>
            <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {result.subqueries.map((sq, i) => (
                <div key={sq.subquery_id || i} className="rounded-xl border border-neutral-200/80 bg-white p-3 shadow-2xs">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-[10px] font-bold text-violet-800 bg-violet-50 px-1.5 py-0.5 rounded border border-violet-200">
                      {sq.subquery_id}
                    </span>
                    {sq.has_evidence ? (
                      <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                        {sq.chunks_found} chunks found
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                        Evidence Gap
                      </span>
                    )}
                  </div>
                  <p className="font-semibold text-neutral-800 text-xs mb-1">
                    "{sq.query_text}"
                  </p>
                  <p className="text-[10px] text-neutral-500">
                    <strong>Intent:</strong> {sq.intent_description}
                  </p>
                  {sq.target_layer_name && (
                    <p className="text-[10px] text-indigo-700 mt-1">
                      <strong>Target:</strong> {sq.target_layer_name}
                    </p>
                  )}
                  {!sq.has_evidence && sq.missing_evidence_statement && (
                    <p className="mt-2 text-[10px] font-medium text-amber-900 bg-amber-50 p-1.5 rounded border border-amber-200">
                      {sq.missing_evidence_statement}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Claim-Level Entailment Section */}
        {result.claim_checks && result.claim_checks.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-neutral-800 uppercase tracking-wider">
                <ShieldCheck size={15} className="text-ocean" />
                <span>Claim-Level NLI Verification</span>
              </div>
              <span className="text-[11px] text-neutral-400 font-medium">
                {result.claim_checks.length} verified statements
              </span>
            </div>

            <div className="grid gap-2.5 sm:grid-cols-2">
              {result.claim_checks.map((claim, idx) => {
                const config = {
                  supported: {
                    icon: CheckCircle2,
                    border: 'border-emerald-200/80',
                    bg: 'bg-emerald-50/50',
                    textColor: 'text-emerald-800',
                    label: 'Supported',
                  },
                  contradicted: {
                    icon: XCircle,
                    border: 'border-red-200/80',
                    bg: 'bg-red-50/50',
                    textColor: 'text-red-800',
                    label: 'Contradicted',
                  },
                  insufficient: {
                    icon: CircleHelp,
                    border: 'border-amber-200/80',
                    bg: 'bg-amber-50/50',
                    textColor: 'text-amber-800',
                    label: 'Insufficient',
                  },
                }[claim.label] || {
                  icon: Info,
                  border: 'border-neutral-200',
                  bg: 'bg-neutral-50',
                  textColor: 'text-neutral-700',
                  label: claim.label,
                }
                const Icon = config.icon

                return (
                  <div
                    key={`${claim.claim}-${idx}`}
                    className={`rounded-2xl border ${config.border} ${config.bg} p-3.5 shadow-2xs`}
                  >
                    <div className="flex items-start gap-2.5">
                      <Icon size={16} className={`shrink-0 mt-0.5 ${config.textColor}`} />
                      <div className="flex-1">
                        <p className="text-xs leading-relaxed font-medium text-ink">
                          {claim.claim}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px] font-bold">
                          <span
                            className={`uppercase tracking-wider ${config.textColor}`}
                          >
                            {config.label}
                          </span>
                          <span className="text-neutral-300">•</span>
                          <span className="text-neutral-500">
                            {Math.round(claim.score * 100)}% Entailed
                          </span>
                          {claim.citation_markers?.length > 0 && (
                            <>
                              <span className="text-neutral-300">•</span>
                              <span className="text-ocean font-bold">
                                {claim.citation_markers.join(', ')}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {/* Retrieved Triad Sources Section */}
        {citations.length > 0 && (
          <section className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-neutral-800 uppercase tracking-wider">
                <BookOpen size={15} className="text-indigo-600" />
                <span>Retrieved Triad Evidence Chunks</span>
              </div>
              <span className="text-[11px] text-neutral-400 font-medium">
                {citations.length} cited sources
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {citations.map((source) => {
                const layer = source.layer || 1
                const layerConfig = {
                  1: {
                    badge: 'bg-indigo-50 border-indigo-200 text-indigo-800',
                    label: 'Layer 1: Foundational (StatPearls)',
                  },
                  2: {
                    badge: 'bg-emerald-50 border-emerald-200 text-emerald-800',
                    label: 'Layer 2: Guidelines (NICE)',
                  },
                  3: {
                    badge: 'bg-purple-50 border-purple-200 text-purple-800',
                    label: 'Layer 3: Trials (PMC/Cochrane)',
                  },
                }[layer] || {
                  badge: 'bg-neutral-100 border-neutral-200 text-neutral-700',
                  label: `Layer ${layer}`,
                }

                return (
                  <a
                    key={source.marker}
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    className="group flex flex-col justify-between rounded-2xl border border-neutral-200/80 bg-white p-4 shadow-2xs no-underline transition hover:border-ocean/40 hover:shadow-sm"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="rounded-md bg-ocean/10 px-2 py-0.5 text-[11px] font-bold text-ocean">
                          {source.marker}
                        </span>
                        <span
                          className={`rounded border px-2 py-0.5 text-[10px] font-semibold ${layerConfig.badge}`}
                        >
                          {source.layer_name || layerConfig.label}
                        </span>
                      </div>

                      {source.breadcrumb?.length > 0 && (
                        <div className="mb-1.5 flex flex-wrap items-center gap-1 text-[10px] font-medium text-neutral-400">
                          {source.breadcrumb.join(' › ')}
                        </div>
                      )}

                      <h4 className="text-xs font-bold leading-snug text-ink group-hover:text-ocean transition">
                        {source.title}
                      </h4>

                      <p className="mt-2 text-xs leading-relaxed text-neutral-500 line-clamp-3">
                        {source.excerpt}
                      </p>
                    </div>

                    <div className="mt-3.5 flex items-center justify-between border-t border-neutral-100 pt-2 text-[10px]">
                      {source.metadata_valid ? (
                        <span className="flex items-center gap-1 font-semibold text-emerald-700">
                          <CheckCircle2 size={12} /> Verified record
                        </span>
                      ) : (
                        <span className="font-semibold text-amber-700">Curated chunk</span>
                      )}
                      <span className="flex items-center gap-1 font-semibold text-ocean">
                        Open source <ExternalLink size={11} />
                      </span>
                    </div>
                  </a>
                )
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

function DDIAlertCard({ report }) {
  if (!report || (!report.has_interaction && (!report.drugs_detected || report.drugs_detected.length < 2))) {
    if (report && report.clinical_summary) {
      return (
        <div className="rounded-2xl border border-blue-200/80 bg-blue-50/60 p-4 text-xs text-blue-900 shadow-2xs">
          <div className="flex items-center gap-2 font-bold mb-1">
            <Info size={15} className="text-blue-700" />
            <span>Medication Identified</span>
          </div>
          <p className="text-blue-800/80 leading-relaxed">{report.clinical_summary}</p>
        </div>
      )
    }
    return null
  }

  const severityConfigs = {
    contraindicated: {
      border: 'border-red-300',
      bg: 'bg-red-50/80',
      badge: 'bg-red-700 text-white',
      badgeText: 'CONTRAINDICATED',
      icon: AlertTriangle,
      iconColor: 'text-red-700',
    },
    major: {
      border: 'border-rose-300',
      bg: 'bg-rose-50/80',
      badge: 'bg-rose-700 text-white',
      badgeText: 'MAJOR INTERACTION',
      icon: AlertTriangle,
      iconColor: 'text-rose-700',
    },
    moderate: {
      border: 'border-amber-300',
      bg: 'bg-amber-50/80',
      badge: 'bg-amber-600 text-white',
      badgeText: 'MODERATE ADJUSTMENT',
      icon: AlertCircle,
      iconColor: 'text-amber-600',
    },
    minor: {
      border: 'border-blue-200',
      bg: 'bg-blue-50/80',
      badge: 'bg-blue-600 text-white',
      badgeText: 'MONITOR',
      icon: Info,
      iconColor: 'text-blue-600',
    },
  }

  const sevKey = report.highest_severity || 'moderate'
  const config = severityConfigs[sevKey] || severityConfigs.moderate
  const SevIcon = config.icon

  return (
    <div className={`rounded-2xl border ${config.border} ${config.bg} p-4 sm:p-5 shadow-2xs`}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200/60 pb-3">
        <div className="flex items-center gap-2">
          <SevIcon className={config.iconColor} size={18} />
          <span className="font-display text-sm font-bold text-ink">
            Drug-Drug Interaction Advisory
          </span>
        </div>
        <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${config.badge}`}>
          {config.badgeText}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className="text-xs font-semibold text-neutral-600">Medications:</span>
        {report.drug_names?.map((name, i) => (
          <span
            key={i}
            className="rounded-lg border border-neutral-200 bg-white px-2 py-0.5 text-xs font-semibold text-ink shadow-2xs"
          >
            💊 {name}
          </span>
        ))}
      </div>

      {report.clinical_summary && (
        <p className="mt-3 text-xs leading-relaxed text-neutral-700">
          <strong className="text-ink">Mechanism: </strong>
          {report.clinical_summary}
        </p>
      )}

      {report.actionable_guidance?.length > 0 && (
        <div className="mt-3 rounded-xl border border-neutral-200/60 bg-white/90 p-3 text-xs text-neutral-800">
          <div className="font-bold text-ink mb-1 flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-emerald-700" /> Actionable Guidance:
          </div>
          <ul className="space-y-1 pl-4 list-disc text-neutral-600">
            {report.actionable_guidance.map((guide, idx) => (
              <li key={idx}>{guide}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
