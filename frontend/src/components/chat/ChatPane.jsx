import { useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  ArrowUp,
  BookOpen,
  Brain,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Copy,
  ExternalLink,
  FileCheck2,
  FlaskConical,
  Info,
  Layers,
  Microscope,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from 'lucide-react'
import { api } from '../../api'
import { cleanLatexMath, parseAnswerBlocks } from './chatUtils'

const starterQuestions = [
  {
    title: 'PD Causes & Guideline Evidence (Multi-Part)',
    query: "What causes Parkinson's disease, and what evidence supports the treatments described in guidelines?",
    tag: 'Selective Decomposition • Triad',
  },
  {
    title: 'NICE NG217 Monotherapy Algorithms',
    query: 'What does NICE NG217 recommend for first-line treatment of focal vs generalized seizures?',
    tag: 'Epilepsy • Guidelines',
  },
  {
    title: 'Sodium Valproate & Lamotrigine Synergy',
    query: 'Can a patient on sodium valproate be safely started on lamotrigine for focal seizures?',
    tag: 'DDI • Valproate • Safety',
  },
  {
    title: 'Hoehn & Yahr Staging & Pharmacotherapy',
    query: "How do Hoehn & Yahr staging and NICE NG71 guide levodopa vs dopamine agonists in Parkinson's?",
    tag: 'Parkinsons • Staging',
  },
]

export default function ChatPane({
  messages,
  question,
  setQuestion,
  submit,
  loading,
  mode,
  endRef,
  onOpenTriad,
}) {
  return (
    <div className="flex h-full flex-col bg-white">
      {/* Messages Stream / Center Canvas */}
      <div className="flex-1 overflow-y-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          {messages.length === 0 ? (
            <WelcomeView submit={submit} mode={mode} onOpenTriad={onOpenTriad} />
          ) : (
            <div className="space-y-6 pb-6">
              {messages.map((message, idx) => (
                <MessageItem key={idx} message={message} />
              ))}
              {loading && <ThinkingIndicator />}
              <div ref={endRef} />
            </div>
          )}
        </div>
      </div>

      {/* Floating Centered Bottom Composer */}
      <div className="border-t border-neutral-200/80 bg-white/95 px-4 py-3.5 backdrop-blur-md sm:px-6">
        <div className="mx-auto max-w-4xl">
          <ChatComposer
            question={question}
            setQuestion={setQuestion}
            submit={submit}
            loading={loading}
            mode={mode}
          />
        </div>
      </div>
    </div>
  )
}

function WelcomeView({ submit, mode, onOpenTriad }) {
  return (
    <div className="my-auto py-8 text-center fade-up">
      <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl border border-ocean/20 bg-mint text-ocean shadow-soft">
        <Microscope size={28} strokeWidth={1.7} />
      </div>

      <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-ocean">
        3-Layer Triad Knowledge Base
      </p>

      <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
        NeuroEvidence Clinical Assistant
      </h1>

      <p className="mx-auto mt-3 max-w-xl text-xs sm:text-sm leading-relaxed text-neutral-500">
        Clinical reasoning assistant grounded in <strong>NCBI Bookshelf</strong>,{' '}
        <strong>NICE Guidelines (NG217 & NG71)</strong>, and <strong>PMC / Cochrane RCTs</strong> with claim-level NLI verification.
      </p>

      {/* Triad Layer Pills */}
      <div className="mx-auto mt-6 flex flex-wrap items-center justify-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-800">
          <BookOpen size={12} /> Layer 1: Bookshelf / StatPearls
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
          <ShieldCheck size={12} /> Layer 2: NICE NG217 & NG71
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-200 bg-purple-50 px-3 py-1 text-xs font-semibold text-purple-800">
          <FlaskConical size={12} /> Layer 3: SANAD II & Cochrane Trials
        </span>
        <button
          onClick={onOpenTriad}
          className="inline-flex items-center gap-1 rounded-full bg-ink px-3 py-1 text-xs font-semibold text-white transition hover:bg-ocean"
        >
          <Layers size={12} /> Architecture
        </button>
      </div>

      {/* Starter Prompts Grid */}
      <div className="mx-auto mt-8 grid max-w-3xl gap-3 text-left sm:grid-cols-2">
        {starterQuestions.map((item, idx) => (
          <button
            key={idx}
            onClick={() => submit(item.query)}
            className="group flex flex-col justify-between rounded-2xl border border-neutral-200/80 bg-white p-4 shadow-2xs transition-all hover:-translate-y-0.5 hover:border-ocean/40 hover:shadow-xs"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-semibold text-ink group-hover:text-ocean transition">
                {item.title}
              </span>
              <ArrowUp
                size={14}
                className="mt-0.5 shrink-0 rotate-45 text-neutral-300 transition group-hover:rotate-90 group-hover:text-ocean"
              />
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-neutral-400 line-clamp-2">
              {item.query}
            </p>
            <div className="mt-3">
              <span className="rounded bg-neutral-100 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-neutral-500">
                {item.tag}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function MessageItem({ message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end fade-up">
        <div className="max-w-2xl rounded-2xl rounded-br-xs bg-ink px-4 py-3 text-xs sm:text-sm leading-relaxed text-white shadow-soft">
          {message.text}
        </div>
      </div>
    )
  }

  if (message.role === 'error') {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-xs sm:text-sm text-red-800 fade-up">
        <AlertTriangle className="mr-2 inline" size={16} />
        {message.text}
      </div>
    )
  }

  return <AssistantMessageCard result={message.result} />
}

function AssistantMessageCard({ result }) {
  const [copied, setCopied] = useState(false)
  const [inspectionOpen, setInspectionOpen] = useState(true)

  function copyAnswer() {
    if (!result?.answer) return
    navigator.clipboard.writeText(result.answer)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <article className="space-y-3 fade-up">
      {/* Header metadata */}
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-neutral-400">
        <span className="grid h-6 w-6 place-items-center rounded-lg bg-ocean text-white font-bold">
          <Brain size={14} />
        </span>
        <span className="font-bold text-ink">NeuroEvidence</span>
        <span>•</span>
        <span>{result.latency_ms} ms</span>
        {result.estimated_cost_usd > 0 && (
          <>
            <span>•</span>
            <span>${result.estimated_cost_usd.toFixed(4)}</span>
          </>
        )}
        {result.demo_mode && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
            Demo Corpus
          </span>
        )}
        {result.mode === 'baseline' && (
          <span className="rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-800">
            Cloud Baseline (Gemini)
          </span>
        )}
        {result.mode === 'ollama_baseline' && (
          <span className="rounded-full bg-purple-50 border border-purple-200 px-2 py-0.5 text-[10px] font-bold text-purple-800">
            Local Baseline (Ollama)
          </span>
        )}
        {result.mode === 'ollama_rag' && (
          <span className="rounded-full bg-purple-100 border border-purple-300 px-2 py-0.5 text-[10px] font-bold text-purple-900">
            Local RAG (Ollama Verified)
          </span>
        )}
        {result.citations?.length > 0 && (
          <span className="rounded-full bg-mint px-2 py-0.5 text-[10px] font-bold text-ocean">
            {result.citations.length} triad sources
          </span>
        )}
        {result.original_answer && (
          <span className="rounded-full bg-sky-50 border border-sky-200 px-2 py-0.5 text-[10px] font-bold text-sky-800">
            Revised via Verification
          </span>
        )}
        {result.subqueries?.length > 1 && (
          <span className="rounded-full bg-violet-50 border border-violet-200 px-2 py-0.5 text-[10px] font-bold text-violet-800">
            {result.subqueries.length} decomposed subqueries
          </span>
        )}
      </div>

      {/* Main Response Box */}
      <div className="rounded-3xl border border-neutral-200/80 bg-white p-5 sm:p-7 shadow-soft">
        {/* Selective Query Decomposition (Multi-Part inquiries) */}
        {result.subqueries?.length > 1 && (
          <SubqueryDecompositionPanel subqueries={result.subqueries} />
        )}

        {/* Warnings */}
        {result.warnings?.length > 0 && (
          <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900">
            <div className="flex items-center gap-2 font-bold mb-1">
              <AlertTriangle size={15} className="text-amber-700" />
              <span>Verification / Clinical Notice</span>
            </div>
            {result.warnings.map((w, i) => (
              <p key={i} className="text-amber-800/80 leading-relaxed">
                {w}
              </p>
            ))}
          </div>
        )}

        {/* Drug-Drug Interaction Advisory */}
        {result.ddi_report && <DDIAlertCard report={result.ddi_report} />}

        {/* Structured Answer Content */}
        <div className="text-xs sm:text-sm leading-relaxed text-ink/90">
          <AnswerContent text={result.answer} citations={result.citations} />
        </div>

        {/* Verification & Claim Entailment Panel */}
        {(result.mode === 'rag_verified' || result.mode === 'ollama_rag') && (
          <VerificationSection
            result={result}
            isOpen={inspectionOpen}
            onToggle={() => setInspectionOpen(!inspectionOpen)}
          />
        )}

        {/* Retrieved Triad Sources */}
        {result.citations?.length > 0 && (
          <SourcesSection citations={result.citations} />
        )}

        {/* Bottom Actions Bar */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 pt-3 text-xs">
          <button
            onClick={copyAnswer}
            className="flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1.5 text-xs font-semibold text-neutral-600 transition hover:bg-neutral-100 hover:text-ink"
          >
            {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
            <span>{copied ? 'Copied' : 'Copy Answer'}</span>
          </button>

          <FeedbackControls traceId={result.trace_id} />
        </div>
      </div>
    </article>
  )
}

function AnswerContent({ text, citations = [] }) {
  if (!text) return null
  const blocks = parseAnswerBlocks(text)

  return (
    <div className="space-y-3">
      {blocks.map((block, idx) => {
        if (block.type === 'h3') {
          return (
            <div key={idx} className="mb-2 mt-4 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-ocean" />
              <h3 className="font-display text-base font-bold text-ink sm:text-lg">
                {renderMarkers(block.content, citations)}
              </h3>
            </div>
          )
        }

        if (block.type === 'h4') {
          return (
            <h4 key={idx} className="mb-1 mt-3 text-xs font-bold uppercase tracking-wider text-ocean">
              {renderMarkers(block.content, citations)}
            </h4>
          )
        }

        if (block.type === 'divider') {
          return <hr key={idx} className="my-3 border-neutral-100" />
        }

        if (block.type === 'disclaimer') {
          return (
            <p key={idx} className="mt-3 border-t border-neutral-100 pt-2 text-xs italic text-neutral-400">
              {renderMarkers(block.content, citations)}
            </p>
          )
        }

        if (block.type === 'bullet_card') {
          return (
            <div
              key={idx}
              className="my-2 rounded-2xl border border-neutral-200/70 bg-neutral-50/50 p-4 transition hover:bg-neutral-50"
            >
              <div className="flex items-start gap-2.5">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ocean" />
                <div className="flex-1 text-sm leading-relaxed text-neutral-700">
                  {renderMarkers(block.parent, citations)}
                </div>
              </div>

              {block.children.length > 0 && (
                <div className="mt-2.5 space-y-2 border-l-2 border-ocean/20 pl-3.5 sm:ml-2 sm:pl-4">
                  {block.children.map((child, cIdx) => (
                    <div key={cIdx} className="text-xs sm:text-sm leading-relaxed text-neutral-600">
                      {renderMarkers(child, citations)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        }

        return (
          <p key={idx} className="leading-7">
            {renderMarkers(block.content, citations)}
          </p>
        )
      })}
    </div>
  )
}

const CITATION_BRACKET_REGEX = /(\[\s*S\d+(?:[\s,;/&+\-–—]+S?\d+)*\s*\]|\*\*.*?\*\*)/g

function renderMarkers(text, citations = []) {
  const sanitized = cleanLatexMath(text)
  const pieces = sanitized.split(CITATION_BRACKET_REGEX)
  return pieces.map((piece, index) => {
    if (!piece) return null

    // Check if piece is a citation bracket, e.g. [S1] or [S1, S4] or [S1, S2, S5, S8]
    const bracketMatch = piece.match(/^\[(\s*S\d+(?:[\s,;/&+\-–—]+S?\d+)*\s*)\]$/)
    if (bracketMatch) {
      const markerNumbers = [...bracketMatch[1].matchAll(/\d+/g)].map((m) => parseInt(m[0], 10))
      return (
        <span key={index} className="inline-flex items-center gap-1 mx-0.5 align-baseline">
          {markerNumbers.map((num) => {
            const marker = `S${num}`
            const citation = citations.find((item) => item.marker === marker)
            const layer = citation?.layer || 1

            const layerStyle =
              {
                1: 'bg-indigo-50 text-indigo-800 border-indigo-200 hover:bg-indigo-100',
                2: 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100',
                3: 'bg-purple-50 text-purple-800 border-purple-200 hover:bg-purple-100',
              }[layer] || 'bg-mint text-ocean border-ocean/20'

            const hasExternalUrl = Boolean(citation?.url && citation.url.startsWith('http'))

            return (
              <a
                key={marker}
                href={hasExternalUrl ? citation.url : '#sources'}
                target={hasExternalUrl ? '_blank' : '_self'}
                rel={hasExternalUrl ? 'noreferrer' : undefined}
                onClick={
                  !hasExternalUrl
                    ? (e) => {
                        e.preventDefault()
                        document.getElementById('sources')?.scrollIntoView({ behavior: 'smooth' })
                      }
                    : undefined
                }
                title={
                  citation?.title
                    ? `${citation.title} (${marker}) — Click to open external publication`
                    : `${marker} — Click to view source details`
                }
                className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-xs font-bold no-underline transition ${layerStyle}`}
              >
                {marker}
              </a>
            )
          })}
        </span>
      )
    }

    const boldMatch = piece.match(/^\*\*(.*?)\*\*$/)
    if (boldMatch) {
      return (
        <strong key={index} className="font-bold text-ink">
          {boldMatch[1]}
        </strong>
      )
    }

    const titleMatch = piece.match(/^([A-Z][A-Za-z0-9\s/&'-]{2,55}:)(\s+[\s\S]*)$/)
    if (titleMatch) {
      return (
        <span key={index}>
          <strong className="font-bold text-ink">{titleMatch[1]}</strong>
          <span className="font-normal text-neutral-700">{titleMatch[2]}</span>
        </span>
      )
    }

    return <span key={index} className="font-normal text-neutral-700">{piece}</span>
  })
}

function renderClaimText(rawClaim) {
  if (!rawClaim) return null
  const cleaned = rawClaim.replace(/^[•\-\*]\s+/, '').trim()

  const colonMatch = cleaned.match(/^(\*{0,2}(.*?)\*{0,2}):\s*([\s\S]*)$/)
  if (colonMatch) {
    const title = colonMatch[2].replace(/\*\*/g, '').trim()
    const body = colonMatch[3].replace(/\*\*/g, '').trim()
    return (
      <span className="leading-snug">
        <strong className="font-bold text-ink">{title}: </strong>
        <span className="font-normal text-neutral-600">{body}</span>
      </span>
    )
  }

  return <span className="font-normal text-neutral-700">{cleaned.replace(/\*\*/g, '')}</span>
}

function VerificationSection({ result, isOpen, onToggle }) {
  const score = result.evidence_score != null ? Math.round(result.evidence_score * 100) : null
  const passed = result.evidence_score != null && result.evidence_score >= (result.evidence_threshold || 0.6)

  const citations = result.citations || []
  const l1Count = citations.filter((c) => (c.layer || 1) === 1).length
  const l2Count = citations.filter((c) => c.layer === 2).length
  const l3Count = citations.filter((c) => c.layer === 3).length

  return (
    <div className="mt-6 rounded-2xl border border-neutral-200/80 bg-[#fafbfa] overflow-hidden">
      <button
        onClick={onToggle}
        className="flex w-full cursor-pointer items-center justify-between p-4 text-left transition hover:bg-neutral-100/60"
      >
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 place-items-center rounded-xl bg-mint text-ocean">
            <FileCheck2 size={17} />
          </div>
          <div>
            <div className="text-xs sm:text-sm font-bold text-ink">Verification & Claim Checks</div>
            <div className="text-[11px] text-neutral-400">
              3-Layer Triad distribution and PubMedBERT NLI claim scoring
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {result.live_pubmed_triggered && (
            <span
              title={`Query: ${result.live_pubmed_query || 'Live E-utilities'}`}
              className="flex items-center gap-1.5 rounded-full bg-cyan-100 px-2.5 py-0.5 text-xs font-bold text-cyan-800 border border-cyan-300"
            >
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-600 animate-pulse" />
              Live PubMed Active
            </span>
          )}
          {score != null && (
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                passed ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
              }`}
            >
              {score}% Grounded
            </span>
          )}
          {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>

      {isOpen && (
        <div className="border-t border-neutral-200/60 p-4 space-y-4">
          {/* Triad Layer Distribution */}
          <div className="grid gap-2.5 sm:grid-cols-3">
            <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-indigo-800">Layer 1: Foundational</span>
                <span className="rounded-full bg-indigo-200 px-2 py-0.5 text-xs font-bold text-indigo-900">
                  {l1Count}
                </span>
              </div>
              <div className="mt-1 text-[10px] text-indigo-700/70">NCBI Bookshelf / StatPearls</div>
            </div>

            <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-emerald-800">Layer 2: Guidelines</span>
                <span className="rounded-full bg-emerald-200 px-2 py-0.5 text-xs font-bold text-emerald-900">
                  {l2Count}
                </span>
              </div>
              <div className="mt-1 text-[10px] text-emerald-700/70">NICE NG217 & NG71</div>
            </div>

            <div className="rounded-xl border border-purple-200 bg-purple-50/60 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-purple-800">Layer 3: Empirical Trials</span>
                <span className="rounded-full bg-purple-200 px-2 py-0.5 text-xs font-bold text-purple-900">
                  {l3Count}
                </span>
              </div>
              <div className="mt-1 text-[10px] text-purple-700/70">
                {result.live_pubmed_triggered ? 'PubMed Live API & Trials' : 'SANAD II & Cochrane Reviews'}
              </div>
            </div>
          </div>

          {/* Live PubMed Query Details (when active) */}
          {result.live_pubmed_triggered && (
            <div className="rounded-xl border border-cyan-200 bg-cyan-50/60 p-3 text-xs text-cyan-900">
              <div className="flex items-center justify-between">
                <span className="font-bold flex items-center gap-1.5 text-cyan-800">
                  <span className="h-2 w-2 rounded-full bg-cyan-600" />
                  Agentic Live PubMed Fallback Triggered
                </span>
                <span className="text-[10px] font-semibold text-cyan-700">NCBI E-Utilities + Neural Rerank</span>
              </div>
              {result.live_pubmed_query && (
                <div className="mt-2 rounded-lg bg-white/80 p-2 font-mono text-[11px] text-cyan-800 border border-cyan-200/50 break-all">
                  <span className="text-[10px] font-bold text-cyan-600 block mb-0.5">FORMULATED MESH QUERY:</span>
                  {result.live_pubmed_query}
                </div>
              )}
            </div>
          )}

          {/* Claim-Level Statements */}
          {result.claim_checks?.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-neutral-500">
                Verified Factual Statements ({result.claim_checks.length})
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {result.claim_checks.map((claim, idx) => {
                  const config = {
                    supported: [CheckCircle2, 'text-emerald-700', 'bg-emerald-50', 'Supported'],
                    contradicted: [XCircle, 'text-red-700', 'bg-red-50', 'Contradicted'],
                    insufficient: [CircleHelp, 'text-amber-700', 'bg-amber-50', 'Insufficient'],
                  }[claim.label] || [Info, 'text-neutral-700', 'bg-neutral-50', claim.label]

                  const [Icon, color, bg, label] = config

                  return (
                    <div key={idx} className={`rounded-xl border border-neutral-200/60 p-3 ${bg}`}>
                      <div className="flex items-start gap-2">
                        <Icon size={15} className={`shrink-0 mt-0.5 ${color}`} />
                        <div>
                          <p className="text-xs text-ink leading-snug">{renderClaimText(claim.claim)}</p>
                          <p className={`mt-1.5 text-[10px] font-bold uppercase tracking-wider ${color}`}>
                            {label} · {Math.round(claim.score * 100)}% · {claim.citation_markers.join(', ')}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Bounded Answer Revision Trace */}
          {result.original_answer && (
            <div className="rounded-xl border border-sky-200/80 bg-sky-50/50 p-3 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sky-950 flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-sky-700" /> Bounded Answer Revision Audit
                </span>
                <span className="text-[10px] font-semibold text-sky-800">
                  Initial Draft Retained
                </span>
              </div>
              <p className="text-[11px] text-sky-900/80 leading-relaxed mb-2">
                Unsupported statements or unverified citations in the draft were repaired through secondary retrieval and NLI verification feedback.
              </p>
              <details className="text-[11px]">
                <summary className="cursor-pointer font-semibold text-sky-800 hover:text-sky-950 select-none">
                  View Initial Pre-Revision Draft ▸
                </summary>
                <div className="mt-2 rounded-lg border border-neutral-200 bg-white p-2.5 font-mono text-[10px] text-neutral-600 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                  {result.original_answer}
                </div>
              </details>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SourcesSection({ citations }) {
  return (
    <div id="sources" className="mt-6 border-t border-neutral-100 pt-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-neutral-500">
          <BookOpen size={15} /> Retrieved Triad Sources
        </div>
        <span className="text-xs text-neutral-400 font-medium">{citations.length} cited entries</span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {citations.map((source) => (
          <a
            key={source.marker}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="group flex flex-col justify-between rounded-2xl border border-neutral-200/80 bg-white p-3.5 no-underline transition hover:border-ocean/40 hover:shadow-2xs"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="rounded bg-mint px-1.5 py-0.5 text-[10px] font-bold text-ocean">
                  {source.marker}
                </span>
                <span className="text-[10px] font-semibold text-neutral-400">
                  {source.layer_source || `Layer ${source.layer}`}
                </span>
              </div>
              <h4 className="text-xs font-bold text-ink group-hover:text-ocean transition line-clamp-1">
                {source.title}
              </h4>
              <p className="mt-1 text-[11px] leading-relaxed text-neutral-500 line-clamp-2">
                {source.excerpt}
              </p>
            </div>

            <div className="mt-3 flex items-center justify-between border-t border-neutral-100 pt-2 text-[10px]">
              <span className="text-emerald-700 font-semibold flex items-center gap-1">
                <CheckCircle2 size={11} /> Verified chunk
              </span>
              <span className="text-ocean font-semibold flex items-center gap-1">
                Open <ExternalLink size={10} />
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  )
}

function SubqueryDecompositionPanel({ subqueries }) {
  const [isOpen, setIsOpen] = useState(true)
  if (!subqueries || subqueries.length <= 1) return null

  const evidenceCount = subqueries.filter((s) => s.has_evidence).length
  const gapCount = subqueries.length - evidenceCount

  return (
    <div className="mb-4 rounded-2xl border border-violet-200/80 bg-violet-50/40 p-4 text-xs shadow-2xs">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex cursor-pointer items-center justify-between select-none"
      >
        <div className="flex items-center gap-2">
          <span className="grid h-6 w-6 place-items-center rounded-lg bg-violet-100 text-violet-800">
            <Layers size={14} />
          </span>
          <div>
            <span className="font-bold text-violet-950">
              Selective Query Decomposition
            </span>
            <span className="ml-2 font-medium text-violet-700/80">
              ({subqueries.length} Information Needs)
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100/80 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
            <CheckCircle2 size={11} /> {evidenceCount} Covered
          </span>
          {gapCount > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
              <AlertTriangle size={11} /> {gapCount} Gap
            </span>
          )}
          <button className="text-violet-600 transition hover:text-violet-950">
            {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="mt-3.5 space-y-2.5 border-t border-violet-200/60 pt-3">
          <p className="text-[11px] leading-relaxed text-violet-900/80">
            The multi-part clinical question was decomposed into focused subqueries preserving clinical constraints, retrieved across Triad layers, and deduplicated:
          </p>
          <div className="grid gap-2">
            {subqueries.map((sq, idx) => {
              const layerColors = {
                1: 'bg-indigo-50 border-indigo-200 text-indigo-800',
                2: 'bg-emerald-50 border-emerald-200 text-emerald-800',
                3: 'bg-purple-50 border-purple-200 text-purple-800',
              }[sq.target_layer] || 'bg-neutral-50 border-neutral-200 text-neutral-800'

              return (
                <div
                  key={sq.subquery_id || idx}
                  className="rounded-xl border border-white/80 bg-white/90 p-3 shadow-2xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-1.5 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-violet-100 px-1.5 py-0.5 font-mono text-[10px] font-bold text-violet-800">
                        {sq.subquery_id}
                      </span>
                      {sq.target_layer && (
                        <span className={`rounded border px-2 py-0.5 text-[10px] font-bold ${layerColors}`}>
                          Layer {sq.target_layer}: {sq.target_layer_name?.split(':')[1]?.trim() || 'Triad'}
                        </span>
                      )}
                    </div>
                    {sq.has_evidence ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                        <CheckCircle2 size={12} /> {sq.chunks_found} sources retrieved
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-700">
                        <AlertTriangle size={12} /> Explicit Gap Identified
                      </span>
                    )}
                  </div>

                  <p className="font-semibold text-ink text-xs mb-1">
                    "{sq.query_text}"
                  </p>
                  <p className="text-[11px] text-neutral-500">
                    <span className="font-semibold text-neutral-600">Information Need:</span> {sq.intent_description}
                  </p>
                  {!sq.has_evidence && sq.missing_evidence_statement && (
                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50/80 p-2 text-[11px] text-amber-900 leading-relaxed">
                      <strong>Unanswered Part Notice:</strong> {sq.missing_evidence_statement}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function DDIAlertCard({ report }) {
  if (!report || (!report.has_interaction && (!report.drugs_detected || report.drugs_detected.length < 2))) {
    return null
  }

  return (
    <div className="mb-5 rounded-2xl border border-amber-300 bg-amber-50/80 p-4 text-xs text-amber-950 shadow-2xs">
      <div className="flex items-center justify-between border-b border-amber-200 pb-2 mb-2">
        <div className="flex items-center gap-2 font-bold">
          <AlertCircle size={16} className="text-amber-700" />
          <span>Drug-Drug Interaction Advisory</span>
        </div>
        <span className="rounded bg-amber-600 px-2 py-0.5 text-[10px] font-bold text-white uppercase">
          {report.highest_severity || 'Warning'}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-2">
        {report.drug_names?.map((d, i) => (
          <span key={i} className="rounded bg-white px-2 py-0.5 font-semibold text-neutral-800 border border-amber-200">
            💊 {d}
          </span>
        ))}
      </div>

      {report.clinical_summary && (
        <p className="text-neutral-700 leading-relaxed mb-2">
          <strong>Mechanism: </strong>
          {report.clinical_summary}
        </p>
      )}

      {report.actionable_guidance?.length > 0 && (
        <ul className="list-disc pl-4 space-y-1 text-neutral-700">
          {report.actionable_guidance.map((g, idx) => (
            <li key={idx}>{g}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function FeedbackControls({ traceId }) {
  const [state, setState] = useState('idle')

  async function send(helpful, issue_type = null) {
    if (state !== 'idle') return
    setState('saving')
    try {
      await api.feedback({ trace_id: traceId, helpful, issue_type })
      setState('saved')
    } catch {
      setState('error')
    }
  }

  if (state === 'saved') {
    return <span className="text-[11px] text-ocean font-semibold">Feedback saved ✓</span>
  }

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-neutral-400 text-[11px]">Helpful?</span>
      <button
        onClick={() => send(true)}
        className="rounded-md border border-neutral-200 p-1.5 text-neutral-500 hover:bg-mint hover:text-ocean transition"
        title="Helpful"
      >
        <ThumbsUp size={13} />
      </button>
      <button
        onClick={() => send(false, 'unsupported_answer')}
        className="rounded-md border border-neutral-200 p-1.5 text-neutral-500 hover:bg-red-50 hover:text-red-700 transition"
        title="Not helpful"
      >
        <ThumbsDown size={13} />
      </button>
    </div>
  )
}

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2.5 text-xs text-neutral-400 py-2">
      <span className="grid h-6 w-6 place-items-center rounded-lg bg-ocean text-white">
        <Brain size={13} />
      </span>
      <div className="flex items-center gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ocean" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ocean [animation-delay:120ms]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ocean [animation-delay:240ms]" />
      </div>
      <span className="text-[11px]">Retrieving across 3-Layer Triad & verifying NLI entailment…</span>
    </div>
  )
}

function ChatComposer({ question, setQuestion, submit, loading, mode }) {
  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div>
      <div className="flex items-end gap-2.5 rounded-2xl border border-neutral-200/90 bg-neutral-50/60 p-2 shadow-soft focus-within:border-ocean/60 focus-within:bg-white transition">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          maxLength={4000}
          placeholder="Ask a clinical question about Parkinson's or Epilepsy..."
          className="max-h-36 min-h-[42px] flex-1 resize-none border-0 bg-transparent px-2 py-2.5 text-xs sm:text-sm outline-none placeholder:text-neutral-400"
        />
        <button
          onClick={() => submit()}
          disabled={loading || !question.trim()}
          className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-ink text-white transition hover:bg-ocean disabled:cursor-not-allowed disabled:opacity-30"
          aria-label="Send message"
        >
          <ArrowUp size={16} />
        </button>
      </div>
      <div className="mt-2 flex items-center justify-between px-1 text-[10px] text-neutral-400">
        <span>Enter to send · Shift+Enter for new line</span>
        <span>
          {mode === 'rag_verified'
            ? 'Cloud RAG: Gemini + Triad + NLI Entailment'
            : mode === 'ollama_rag'
            ? 'Local RAG: Ollama + Triad + NLI Entailment'
            : mode === 'ollama_baseline'
            ? 'Local Baseline: Ollama (On-Device Zero-Shot)'
            : 'Cloud Baseline: Gemini (Parametric Zero-Shot)'}
        </span>
      </div>
    </div>
  )
}
