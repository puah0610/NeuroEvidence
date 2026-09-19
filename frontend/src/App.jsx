import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowUp,
  BarChart3,
  BookOpen,
  Brain,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  ExternalLink,
  FileCheck2,
  FlaskConical,
  HeartPulse,
  Info,
  Layers,
  Menu,
  MessageSquareText,
  Microscope,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  X,
  XCircle,
} from 'lucide-react'
import { api } from './api'

const starterQuestions = [
  "What does NICE NG217 recommend for first-line treatment of focal vs generalized seizures?",
  "What were the SANAD II trial findings comparing levetiracetam to valproate and lamotrigine?",
  "How do Hoehn & Yahr staging and NICE NG71 guide levodopa vs dopamine agonists in Parkinson's?",
  "What does empirical trial evidence show comparing MAO-B inhibitors vs COMT inhibitors for motor fluctuations?",
]

const emptySession = () => `session-${crypto.randomUUID()}`

export default function App() {
  const [view, setView] = useState('chat')
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState('rag_verified')
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState(null)
  const [summary, setSummary] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [triadModalOpen, setTriadModalOpen] = useState(false)
  const [sessionId, setSessionId] = useState(emptySession)
  const endRef = useRef(null)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: 'degraded', demo_mode: true }))
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  useEffect(() => {
    if (view === 'evaluation') api.summary().then(setSummary).catch(() => setSummary(null))
  }, [view])

  async function submit(value = question) {
    const clean = value.trim()
    if (!clean || loading) return
    setQuestion('')
    setMessages((current) => [...current, { role: 'user', text: clean }])
    setLoading(true)
    try {
      const result = await api.chat({ session_id: sessionId, question: clean, mode })
      setMessages((current) => [...current, { role: 'assistant', result }])
    } catch (error) {
      const detail = error.response?.data?.detail || 'The assistant could not reach the research API.'
      setMessages((current) => [...current, { role: 'error', text: detail }])
    } finally {
      setLoading(false)
    }
  }

  function newSession() {
    setMessages([])
    setSessionId(emptySession())
    setSidebarOpen(false)
    setView('chat')
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <Header health={health} onMenu={() => setSidebarOpen(true)} onOpenTriad={() => setTriadModalOpen(true)} />
      <div className="mx-auto flex min-h-[calc(100vh-73px)] max-w-[1600px]">
        <Sidebar
          open={sidebarOpen}
          view={view}
          setView={(next) => { setView(next); setSidebarOpen(false) }}
          mode={mode}
          setMode={setMode}
          onClose={() => setSidebarOpen(false)}
          onNew={newSession}
          onOpenTriad={() => setTriadModalOpen(true)}
        />
        <main className="min-w-0 flex-1">
          {view === 'chat' ? (
            <ChatView
              messages={messages}
              question={question}
              setQuestion={setQuestion}
              submit={submit}
              loading={loading}
              mode={mode}
              endRef={endRef}
              onOpenTriad={() => setTriadModalOpen(true)}
            />
          ) : (
            <EvaluationView summary={summary} />
          )}
        </main>
      </div>
      {triadModalOpen && <TriadModal onClose={() => setTriadModalOpen(false)} />}
    </div>
  )
}

function Header({ health, onMenu, onOpenTriad }) {
  return (
    <header className="sticky top-0 z-30 border-b border-ink/10 bg-paper/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[73px] max-w-[1600px] items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <button onClick={onMenu} className="rounded-xl p-2 hover:bg-ink/5 lg:hidden" aria-label="Open navigation">
            <Menu size={21} />
          </button>
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-ink text-white shadow-soft">
            <Brain size={23} strokeWidth={1.8} />
          </div>
          <div>
            <div className="font-display text-xl font-bold tracking-tight">NeuroEvidence</div>
            <div className="hidden text-[10px] font-bold uppercase tracking-[0.2em] text-ink/45 sm:block">
              3-Layer Triad Assistant • PD & Epilepsy
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenTriad}
            className="hidden items-center gap-1.5 rounded-full border border-ocean/20 bg-mint/60 px-3 py-1.5 text-xs font-bold text-ocean transition hover:bg-ocean hover:text-white sm:inline-flex"
          >
            <Layers size={14} /> 3-Layer Triad KB
          </button>
          <div className="flex items-center gap-2 rounded-full border border-ink/10 bg-white px-3 py-1.5 text-xs font-semibold shadow-sm">
            <span className={`h-2 w-2 rounded-full ${health?.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            {health?.demo_mode ? 'Demo corpus' : 'Research corpus'}
          </div>
        </div>
      </div>
    </header>
  )
}

function Sidebar({ open, view, setView, mode, setMode, onClose, onNew, onOpenTriad }) {
  return (
    <>
      {open && <button className="fixed inset-0 z-40 bg-ink/35 lg:hidden" onClick={onClose} aria-label="Close navigation" />}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-[286px] flex-col border-r border-ink/10 bg-[#f0f1eb] px-4 pb-5 pt-4 transition-transform lg:sticky lg:top-[73px] lg:z-10 lg:h-[calc(100vh-73px)] lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="mb-5 flex justify-end lg:hidden">
          <button onClick={onClose} className="rounded-xl p-2 hover:bg-ink/5" aria-label="Close navigation"><X size={20} /></button>
        </div>
        <button onClick={onNew} className="mb-6 flex w-full items-center justify-between rounded-2xl bg-ink px-4 py-3.5 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-[#183654]">
          New conversation <MessageSquareText size={17} />
        </button>

        <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-ink/40">Workspace</p>
        <nav className="space-y-1">
          <NavButton active={view === 'chat'} icon={MessageSquareText} label="Assistant" onClick={() => setView('chat')} />
          <NavButton active={view === 'evaluation'} icon={BarChart3} label="Evaluation" onClick={() => setView('evaluation')} />
        </nav>

        <div className="mt-6">
          <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-ink/40">Knowledge Base</p>
          <button
            onClick={onOpenTriad}
            className="flex w-full items-center gap-3 rounded-2xl border border-ink/10 bg-white p-3 text-left transition hover:border-ocean/40"
          >
            <div className="grid h-8 w-8 place-items-center rounded-xl bg-mint text-ocean">
              <Layers size={17} />
            </div>
            <div>
              <div className="text-xs font-bold text-ink">3-Layer Triad</div>
              <div className="text-[10px] text-ink/50">Bookshelf • NICE • PMC</div>
            </div>
            <ChevronRight size={14} className="ml-auto text-ink/40" />
          </button>
        </div>

        <div className="mt-6">
          <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-ink/40">Research mode</p>
          <div className="rounded-2xl border border-ink/10 bg-white p-1.5 shadow-sm">
            <ModeButton active={mode === 'rag_verified'} onClick={() => setMode('rag_verified')} icon={ShieldCheck} title="RAG + verification" subtitle="Hybrid retrieval & NLI" />
            <ModeButton active={mode === 'baseline'} onClick={() => setMode('baseline')} icon={FlaskConical} title="Plain LLM baseline" subtitle="No retrieval checks" />
          </div>
        </div>

        <div className="mt-auto rounded-2xl border border-coral/20 bg-[#fff7f3] p-4">
          <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-coral"><HeartPulse size={16} /> Safety notice</div>
          <p className="text-xs leading-5 text-ink/65">For education and research only. Not for diagnosis, prescribing, or emergency decisions.</p>
        </div>
      </aside>
    </>
  )
}

function NavButton({ active, icon: Icon, label, onClick }) {
  return <button onClick={onClick} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold ${active ? 'bg-white text-ocean shadow-sm' : 'text-ink/60 hover:bg-white/60 hover:text-ink'}`}><Icon size={18} />{label}<ChevronRight className="ml-auto" size={15} /></button>
}

function ModeButton({ active, onClick, icon: Icon, title, subtitle }) {
  return <button onClick={onClick} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition ${active ? 'bg-mint text-ocean' : 'text-ink/55 hover:bg-paper'}`}><Icon size={18} /><span><span className="block text-xs font-bold">{title}</span><span className="block text-[10px] opacity-65">{subtitle}</span></span>{active && <Check size={15} className="ml-auto" />}</button>
}

function ChatView({ messages, question, setQuestion, submit, loading, mode, endRef, onOpenTriad }) {
  const isEmpty = messages.length === 0
  return (
    <div className="paper-grid flex min-h-[calc(100vh-73px)] flex-col">
      <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-8 sm:px-7 lg:py-12">
        {isEmpty ? (
          <Welcome submit={submit} mode={mode} onOpenTriad={onOpenTriad} />
        ) : (
          <div className="space-y-8 pb-8">
            {messages.map((message, index) => <Message key={index} message={message} />)}
            {loading && <Thinking />}
            <div ref={endRef} />
          </div>
        )}
      </div>
      <Composer question={question} setQuestion={setQuestion} submit={submit} loading={loading} mode={mode} />
    </div>
  )
}

function Welcome({ submit, mode, onOpenTriad }) {
  return (
    <section className="mx-auto my-auto w-full max-w-4xl py-10 text-center fade-up">
      <div className="mx-auto mb-6 grid h-16 w-16 place-items-center rounded-2xl border border-ocean/15 bg-mint text-ocean shadow-soft">
        <Microscope size={31} strokeWidth={1.6} />
      </div>
      <p className="mb-3 text-xs font-bold uppercase tracking-[0.24em] text-ocean">3-Layer Triad Knowledge Base</p>
      <h1 className="mx-auto max-w-3xl font-display text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
        Parkinson's & Epilepsy Assistant.<br />
        <span className="italic text-ocean">Grounded across 3 evidence layers.</span>
      </h1>
      <p className="mx-auto mt-5 max-w-2xl text-sm leading-6 text-ink/60 sm:text-base">
        Explore clinical questions synthesized from <strong>Foundational Knowledge (NCBI Bookshelf)</strong>,{' '}
        <strong>Clinical Guidelines (NICE)</strong>, and <strong>Empirical Trials (PMC / Cochrane)</strong> with verified claim-level checks.
      </p>

      {/* 3-Layer Triad Visual Pills */}
      <div className="mx-auto mt-7 flex max-w-3xl flex-wrap items-center justify-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-800">
          <BookOpen size={13} /> Layer 1: Bookshelf / StatPearls
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
          <ShieldCheck size={13} /> Layer 2: NICE NG217 & NG71
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-200 bg-purple-50 px-3 py-1 text-xs font-semibold text-purple-800">
          <FlaskConical size={13} /> Layer 3: SANAD II & Cochrane Trials
        </span>
        <button
          onClick={onOpenTriad}
          className="inline-flex items-center gap-1 rounded-full bg-ink px-3 py-1 text-xs font-semibold text-white transition hover:bg-ocean"
        >
          View Architecture <ChevronRight size={13} />
        </button>
      </div>

      <div className="mx-auto mt-8 grid max-w-3xl gap-3 text-left sm:grid-cols-2">
        {starterQuestions.map((item) => (
          <button
            key={item}
            onClick={() => submit(item)}
            className="group flex min-h-24 items-start justify-between rounded-2xl border border-ink/10 bg-white/85 p-4 text-sm font-semibold leading-5 shadow-sm transition hover:-translate-y-1 hover:border-ocean/30 hover:shadow-soft"
          >
            <span>{item}</span>
            <ArrowUp className="ml-3 mt-0.5 rotate-45 text-ocean transition group-hover:rotate-90" size={17} />
          </button>
        ))}
      </div>
      <div className="mt-7 inline-flex items-center gap-2 rounded-full bg-white px-3 py-2 text-xs text-ink/50 shadow-sm">
        <Info size={14} /> Active mode: {mode === 'rag_verified' ? 'Hybrid Dense + Sparse RAG with NLI Verification' : 'Plain LLM baseline'}
      </div>
    </section>
  )
}

function Message({ message }) {
  if (message.role === 'user') return <div className="ml-auto max-w-2xl rounded-[22px] rounded-br-md bg-ink px-5 py-4 text-sm leading-6 text-white shadow-soft fade-up">{message.text}</div>
  if (message.role === 'error') return <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"><AlertTriangle className="mr-2 inline" size={17} />{message.text}</div>
  return <AssistantMessage result={message.result} />
}

function AssistantMessage({ result }) {
  return (
    <article className="fade-up">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-ink/50">
        <span className="grid h-8 w-8 place-items-center rounded-xl bg-ocean text-white"><Brain size={17} /></span>
        <span className="font-bold text-ink">NeuroEvidence</span>
        <span>•</span><span>{result.latency_ms} ms</span>
        {result.estimated_cost_usd > 0 && <><span>•</span><span>${result.estimated_cost_usd.toFixed(4)}</span></>}
        {result.demo_mode && <span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-800">Demo</span>}
        {result.citations?.length > 0 && (
          <span className="rounded-full bg-mint px-2 py-0.5 text-[11px] font-bold text-ocean">
            {result.citations.length} sources across triad
          </span>
        )}
      </div>
      <div className="rounded-3xl border border-ink/10 bg-white p-5 shadow-soft sm:p-7">
        {result.warnings?.length > 0 && <Warnings warnings={result.warnings} intent={result.intent} />}
        <div className="answer-copy">
          <AnswerContent text={result.answer} citations={result.citations} />
        </div>
        {result.mode === 'rag_verified' && result.evidence_score != null && <VerificationPanel result={result} />}
        {result.citations?.length > 0 && <Sources citations={result.citations} />}
        <Feedback traceId={result.trace_id} />
      </div>
    </article>
  )
}

function renderMarkers(text, citations = []) {
  const pieces = text.split(/(\[S\d+\]|\*\*.*?\*\*)/g)
  return pieces.map((piece, index) => {
    if (!piece) return null
    const match = piece.match(/^\[S(\d+)\]$/)
    if (match) {
      const marker = `S${match[1]}`
      const citation = citations.find((item) => item.marker === marker)
      const layer = citation?.layer || 1

      const layerStyle = {
        1: 'bg-indigo-50 text-indigo-800 border-indigo-200 hover:bg-indigo-100',
        2: 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100',
        3: 'bg-purple-50 text-purple-800 border-purple-200 hover:bg-purple-100',
      }[layer] || 'bg-mint text-ocean border-ocean/20'

      return (
        <a
          key={index}
          href={citation?.url || '#sources'}
          target="_blank"
          rel="noreferrer"
          title={`${citation?.layer_name || `Layer ${layer}`} • ${citation?.title || marker}`}
          className={`mx-0.5 inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-bold no-underline transition ${layerStyle}`}
        >
          <span>{marker}</span>
          <span className="rounded bg-black/5 px-1 py-0.2 text-[9px] font-bold">L{layer}</span>
        </a>
      )
    }

    const boldMatch = piece.match(/^\*\*(.*?)\*\*$/)
    if (boldMatch) {
      return (
        <strong key={index} className="font-semibold text-ink">
          {boldMatch[1]}
        </strong>
      )
    }

    return <span key={index}>{piece}</span>
  })
}

function AnswerContent({ text, citations = [] }) {
  if (!text) return null
  const lines = text.split(/\n+/).map((l) => l.trim()).filter(Boolean)

  return (
    <div className="space-y-3 text-[15px] leading-relaxed text-ink/85">
      {lines.map((line, idx) => {
        // H3: Main Topic
        if (line.startsWith('### ')) {
          const content = line.replace(/^###\s+/, '')
          return (
            <div key={idx} className="mb-2 mt-1 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-ocean" />
              <h3 className="font-display text-base font-bold text-ink sm:text-lg">
                {renderMarkers(content, citations)}
              </h3>
            </div>
          )
        }

        // H4: Subheading
        if (line.startsWith('#### ')) {
          const content = line.replace(/^####\s+/, '')
          return (
            <h4 key={idx} className="mb-1.5 mt-3 text-xs font-bold uppercase tracking-wider text-ocean">
              {renderMarkers(content, citations)}
            </h4>
          )
        }

        // Bullet point: starts with • or - or *
        if (/^[•\-\*]\s+/.test(line)) {
          const content = line.replace(/^[•\-\*]\s+/, '')
          return (
            <div
              key={idx}
              className="my-1.5 flex items-start gap-3 rounded-2xl border border-ink/5 bg-ink/[0.015] p-3.5 transition hover:border-ocean/20 hover:bg-mint/10"
            >
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ocean" />
              <div className="flex-1 leading-relaxed">
                {renderMarkers(content, citations)}
              </div>
            </div>
          )
        }

        // Educational notice / disclaimer
        if (
          line.includes('summarizes the retrieved educational material') ||
          line.includes('individual diagnosis') ||
          line.includes('simulated plain-model baseline')
        ) {
          return (
            <p key={idx} className="mt-4 border-t border-ink/5 pt-3 text-xs italic text-ink/50">
              {renderMarkers(line, citations)}
            </p>
          )
        }

        // Regular paragraph
        return (
          <p key={idx} className="leading-7">
            {renderMarkers(line, citations)}
          </p>
        )
      })}
    </div>
  )
}

function LayerBadge({ layer = 1, layerName, layerSource, compact = false }) {
  const configs = {
    1: {
      bg: 'bg-indigo-50 border-indigo-200 text-indigo-800',
      pill: 'bg-indigo-100 text-indigo-800',
      label: 'Layer 1: Foundational Knowledge',
      source: 'NCBI Bookshelf / StatPearls',
      icon: BookOpen,
    },
    2: {
      bg: 'bg-emerald-50 border-emerald-200 text-emerald-800',
      pill: 'bg-emerald-100 text-emerald-800',
      label: 'Layer 2: Clinical Guidelines',
      source: 'NICE Guidelines',
      icon: ShieldCheck,
    },
    3: {
      bg: 'bg-purple-50 border-purple-200 text-purple-800',
      pill: 'bg-purple-100 text-purple-800',
      label: 'Layer 3: Empirical Trials',
      source: 'PubMed Central / Cochrane',
      icon: FlaskConical,
    },
  }
  const config = configs[layer] || configs[1]
  const Icon = config.icon

  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold ${config.pill}`}>
        <Icon size={10} /> L{layer}
      </span>
    )
  }

  return (
    <div className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold shadow-xs ${config.bg}`}>
      <Icon size={13} className="shrink-0" />
      <span className="font-bold">{layerName || config.label}</span>
      <span className="opacity-70 text-[11px]">• {layerSource || config.source}</span>
    </div>
  )
}

function Warnings({ warnings, intent }) {
  const safety = intent !== 'educational_in_scope'
  return <div className={`mb-5 rounded-2xl border p-4 ${safety ? 'border-coral/25 bg-[#fff5f1]' : 'border-amber-200 bg-amber-50'}`}><div className="flex gap-3"><AlertTriangle className={safety ? 'text-coral' : 'text-amber-600'} size={19} /><div><div className="mb-1 text-xs font-bold uppercase tracking-wider">{safety ? 'Safety response' : 'Verification notice'}</div>{warnings.map((warning) => <p key={warning} className="text-xs leading-5 text-ink/65">{warning}</p>)}</div></div></div>
}

function VerificationPanel({ result }) {
  const score = Math.round(result.evidence_score * 100)
  const passed = result.evidence_score >= result.evidence_threshold

  const l1Count = result.citations.filter((c) => (c.layer || 1) === 1).length
  const l2Count = result.citations.filter((c) => c.layer === 2).length
  const l3Count = result.citations.filter((c) => c.layer === 3).length

  return (
    <details className="mt-7 overflow-hidden rounded-2xl border border-ink/10 bg-[#fafbf8]" open>
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-4 sm:px-5">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-mint text-ocean"><FileCheck2 size={19} /></div>
        <div>
          <div className="text-sm font-bold">How this answer was verified</div>
          <div className="text-xs text-ink/50">3-Layer Triad distribution, metadata and claim checks</div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className={`text-xs font-bold ${passed ? 'text-ocean' : 'text-amber-700'}`}>{passed ? 'Threshold met' : 'Review needed'}</span>
          <ChevronRight size={16} />
        </div>
      </summary>
      <div className="border-t border-ink/10 p-4 sm:p-5">
        {/* 3-Layer Triad Breakdown Bar */}
        <div className="mb-5 rounded-2xl border border-ink/10 bg-white p-4">
          <div className="mb-3 flex items-center justify-between text-xs font-bold text-ink">
            <span className="flex items-center gap-1.5"><Layers size={15} className="text-ocean" /> 3-Layer Evidence Triad Coverage</span>
            <span className="text-[11px] font-normal text-ink/50">{result.citations.length} total cited chunks</span>
          </div>
          <div className="grid gap-2.5 sm:grid-cols-3">
            <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-indigo-800">Layer 1: Foundational</span>
                <span className="rounded-full bg-indigo-200 px-2 py-0.5 text-xs font-bold text-indigo-900">{l1Count}</span>
              </div>
              <div className="mt-1 text-[10px] text-indigo-700/70">NCBI Bookshelf / StatPearls</div>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-emerald-800">Layer 2: Guidelines</span>
                <span className="rounded-full bg-emerald-200 px-2 py-0.5 text-xs font-bold text-emerald-900">{l2Count}</span>
              </div>
              <div className="mt-1 text-[10px] text-emerald-700/70">NICE NG217 & NG71</div>
            </div>
            <div className="rounded-xl border border-purple-200 bg-purple-50/70 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-purple-800">Layer 3: Empirical Trials</span>
                <span className="rounded-full bg-purple-200 px-2 py-0.5 text-xs font-bold text-purple-900">{l3Count}</span>
              </div>
              <div className="mt-1 text-[10px] text-purple-700/70">SANAD II & Cochrane Meta-Analyses</div>
            </div>
          </div>
        </div>

        <div className="grid gap-5 md:grid-cols-[150px_1fr]">
          <div className="flex flex-col items-center justify-center rounded-2xl bg-white p-4">
            <div className="score-ring grid h-24 w-24 place-items-center rounded-full" style={{ '--score': `${score}%` }}>
              <div className="grid h-[76px] w-[76px] place-items-center rounded-full bg-white">
                <span className="font-display text-2xl font-bold">{score}</span>
              </div>
            </div>
            <div className="mt-3 text-center text-xs font-bold">Evidence Support Score</div>
            <div className="mt-1 text-center text-[10px] leading-4 text-ink/45">Not medical certainty</div>
          </div>
          <div className="space-y-2">
            {result.claim_checks.length ? (
              result.claim_checks.map((claim, index) => <ClaimRow key={`${claim.claim}-${index}`} claim={claim} />)
            ) : (
              <div className="rounded-xl bg-white p-4 text-sm text-ink/55">No factual claims with source markers were detected.</div>
            )}
          </div>
        </div>
      </div>
    </details>
  )
}

function ClaimRow({ claim }) {
  const config = {
    supported: [CheckCircle2, 'text-emerald-700', 'bg-emerald-50', 'Supported'],
    contradicted: [XCircle, 'text-red-700', 'bg-red-50', 'Contradicted'],
    insufficient: [CircleHelp, 'text-amber-700', 'bg-amber-50', 'Insufficient'],
  }[claim.label]
  const [Icon, color, background, label] = config
  return (
    <div className={`rounded-xl p-3.5 ${background}`}>
      <div className="flex gap-3">
        <Icon className={`mt-0.5 shrink-0 ${color}`} size={18} />
        <div>
          <div className="text-sm font-medium leading-5">{claim.claim}</div>
          <div className={`mt-1.5 text-[10px] font-bold uppercase tracking-wider ${color}`}>
            {label} · {Math.round(claim.score * 100)}% · {claim.citation_markers.join(', ')}
          </div>
        </div>
      </div>
    </div>
  )
}

function Sources({ citations }) {
  return (
    <section id="sources" className="mt-7 border-t border-ink/10 pt-6">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-ink/50">
          <BookOpen size={16} /> Retrieved Triad Sources
        </div>
        <span className="text-xs font-semibold text-ink/45">{citations.length} cited entries</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {citations.map((source) => (
          <a
            key={source.marker}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="group flex flex-col justify-between rounded-2xl border border-ink/10 bg-white p-4 no-underline transition hover:border-ocean/30 hover:bg-mint/20"
          >
            <div>
              <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
                <span className="rounded-lg bg-mint px-2 py-1 text-[10px] font-bold text-ocean">
                  {source.marker}
                </span>
                <LayerBadge
                  layer={source.layer || 1}
                  layerName={source.layer_name}
                  layerSource={source.layer_source}
                />
              </div>

              {source.subtopic && (
                <div className="mb-1.5">
                  <span className="rounded bg-ink/5 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-ink/60">
                    {source.subtopic}
                  </span>
                </div>
              )}

              <div className="text-sm font-bold leading-5 text-ink group-hover:text-ocean">
                {source.title}
              </div>
              <div className="mt-2 line-clamp-3 text-xs leading-5 text-ink/60">
                {source.excerpt}
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between border-t border-ink/5 pt-2.5">
              {source.metadata_valid ? (
                <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-700">
                  <CheckCircle2 size={13} /> Verified record
                </span>
              ) : (
                <span className="text-[10px] font-bold text-amber-700">Unverified</span>
              )}
              <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-ocean">
                Inspect Source <ExternalLink size={12} />
              </span>
            </div>
          </a>
        ))}
      </div>
    </section>
  )
}

function Feedback({ traceId }) {
  const [state, setState] = useState('idle')
  async function send(helpful, issue_type = null) {
    if (state !== 'idle') return
    setState('saving')
    try { await api.feedback({ trace_id: traceId, helpful, issue_type }); setState('saved') } catch { setState('error') }
  }
  return (
    <div className="mt-6 flex items-center justify-end gap-2 border-t border-ink/10 pt-4 text-xs text-ink/45">
      <span className="mr-1">Was this useful?</span>
      {state === 'saved' ? (
        <span className="flex items-center gap-1 font-semibold text-ocean"><Check size={14} /> Feedback saved</span>
      ) : (
        <>
          <button onClick={() => send(true)} className="rounded-lg border border-ink/10 p-2 hover:bg-mint hover:text-ocean" aria-label="Helpful"><ThumbsUp size={15} /></button>
          <button onClick={() => send(false, 'unsupported_answer')} className="rounded-lg border border-ink/10 p-2 hover:bg-red-50 hover:text-red-700" aria-label="Not helpful"><ThumbsDown size={15} /></button>
        </>
      )}
    </div>
  )
}

function Thinking() {
  return (
    <div className="flex items-center gap-3 text-sm text-ink/50 fade-up">
      <div className="grid h-8 w-8 place-items-center rounded-xl bg-ocean text-white"><Brain size={17} /></div>
      <div className="flex items-center gap-1.5">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ocean" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ocean [animation-delay:120ms]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ocean [animation-delay:240ms]" />
      </div>
      <span>Retrieving across 3-Layer Triad (Bookshelf, NICE, PMC) & checking NLI…</span>
    </div>
  )
}

function Composer({ question, setQuestion, submit, loading, mode }) {
  function keyDown(event) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }
  return (
    <div className="sticky bottom-0 border-t border-ink/10 bg-paper/90 px-4 py-4 backdrop-blur-xl sm:px-7">
      <div className="mx-auto max-w-4xl">
        <div className="flex items-end gap-3 rounded-2xl border border-ink/15 bg-white p-2 pl-4 shadow-soft focus-within:border-ocean/50">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={keyDown}
            rows={1}
            maxLength={4000}
            placeholder="Ask an educational clinical question on Parkinson's disease or epilepsy…"
            className="max-h-32 min-h-11 flex-1 resize-none border-0 bg-transparent py-3 text-sm outline-none placeholder:text-ink/35"
          />
          <button
            onClick={() => submit()}
            disabled={loading || !question.trim()}
            className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-ocean text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:opacity-35"
            aria-label="Send question"
          >
            <ArrowUp size={19} />
          </button>
        </div>
        <div className="mt-2 flex items-center justify-between px-1 text-[10px] text-ink/40">
          <span>{mode === 'rag_verified' ? '3-Layer Triad RAG (Dense + Sparse) with NLI verification' : 'Unverified research baseline'}</span>
          <span>Educational use only</span>
        </div>
      </div>
    </div>
  )
}

function TriadModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4 backdrop-blur-xs fade-up">
      <div className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-ink/10 bg-white p-6 shadow-2xl sm:p-8">
        <div className="flex items-center justify-between border-b border-ink/10 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-mint text-ocean">
              <Layers size={22} />
            </div>
            <div>
              <h2 className="font-display text-xl font-bold">The 3-Layer Triad Knowledge Base</h2>
              <p className="text-xs text-ink/50">Parkinson's Disease and Epilepsy Architecture</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-xl p-2 text-ink/40 hover:bg-ink/5 hover:text-ink" aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <div className="mt-6 space-y-4">
          {/* Layer 1 */}
          <div className="rounded-2xl border border-indigo-200 bg-indigo-50/50 p-5">
            <div className="mb-2 flex items-center gap-2 text-indigo-900 font-bold">
              <BookOpen size={18} />
              <span>Layer 1: Foundational Knowledge (NCBI Bookshelf / StatPearls)</span>
            </div>
            <div className="grid gap-3 text-xs sm:grid-cols-2 text-indigo-950">
              <div className="rounded-xl bg-white p-3 border border-indigo-100">
                <span className="font-bold block mb-1">Epilepsy</span>
                • ILAE 2017 Seizure & Epilepsy Classification<br />
                • Seizure Semiology & Cortical Hypersynchrony<br />
                • Anti-seizure Medication (ASM) Cellular Targets
              </div>
              <div className="rounded-xl bg-white p-3 border border-indigo-100">
                <span className="font-bold block mb-1">Parkinson's Disease</span>
                • SNpc Dopaminergic Loss & Alpha-Synuclein Pathology<br />
                • Hoehn and Yahr Clinical Staging (Stages 1–5)<br />
                • Core Pharmacology (Levodopa/Carbidopa, Agonists, MAO-B)
              </div>
            </div>
          </div>

          {/* Layer 2 */}
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5">
            <div className="mb-2 flex items-center gap-2 text-emerald-900 font-bold">
              <ShieldCheck size={18} />
              <span>Layer 2: Clinical Guidelines & Consensus (NICE Guidelines)</span>
            </div>
            <div className="grid gap-3 text-xs sm:grid-cols-2 text-emerald-950">
              <div className="rounded-xl bg-white p-3 border border-emerald-100">
                <span className="font-bold block mb-1">NICE NG217 (Epilepsies)</span>
                • First Seizure Presentation (Specialist review &lt;2 weeks)<br />
                • Monotherapy Algorithms (Focal vs Generalized)<br />
                • Teratogenicity & Valproate Pregnancy Prevention (Prevent)
              </div>
              <div className="rounded-xl bg-white p-3 border border-emerald-100">
                <span className="font-bold block mb-1">NICE NG71 (Parkinson's)</span>
                • Specialist Diagnosis (UK Brain Bank Criteria)<br />
                • First-Line Treatment Stratified by Quality of Life<br />
                • Motor Fluctuation Management & Advanced Care (DBS)
              </div>
            </div>
          </div>

          {/* Layer 3 */}
          <div className="rounded-2xl border border-purple-200 bg-purple-50/50 p-5">
            <div className="mb-2 flex items-center gap-2 text-purple-900 font-bold">
              <FlaskConical size={18} />
              <span>Layer 3: Empirical Evidence & Trials (PubMed Central / Cochrane)</span>
            </div>
            <div className="grid gap-3 text-xs sm:grid-cols-2 text-purple-950">
              <div className="rounded-xl bg-white p-3 border border-purple-100">
                <span className="font-bold block mb-1">Comparative RCTs (SANAD II)</span>
                • Generalized Arm: Levetiracetam vs Valproate (Lancet 2021)<br />
                • Focal Arm: Levetiracetam vs Lamotrigine (Lancet 2021)<br />
                • Long-term remission, treatment retention & safety trade-offs
              </div>
              <div className="rounded-xl bg-white p-3 border border-purple-100">
                <span className="font-bold block mb-1">Systematic Reviews & Meta-Analyses</span>
                • STN vs GPi Deep Brain Stimulation (DBS) 5–10yr outcomes<br />
                • MAO-B vs COMT Inhibitors in Levodopa Motor Fluctuations<br />
                • Cochrane evidence on 'off' time reduction & adverse profiles
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-xl bg-ink px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-ocean"
          >
            Close Overview
          </button>
        </div>
      </div>
    </div>
  )
}

function EvaluationView({ summary }) {
  const cards = useMemo(() => [
    ['Recorded traces', summary?.total_traces ?? 0, Activity, 'All local experiments'],
    ['Average score', summary?.average_evidence_score != null ? `${Math.round(summary.average_evidence_score * 100)}%` : '—', ShieldCheck, 'Verified mode only'],
    ['Average latency', summary?.average_latency_ms != null ? `${summary.average_latency_ms} ms` : '—', Clock3, 'Across all modes'],
    ['Estimated API cost', summary?.total_estimated_cost_usd ? `$${summary.total_estimated_cost_usd.toFixed(4)}` : '$0.0000', FlaskConical, `${(summary?.total_input_tokens ?? 0) + (summary?.total_output_tokens ?? 0)} tokens`],
    ['Feedback entries', summary?.feedback_count ?? 0, MessageSquareText, summary?.helpful_rate != null ? `${Math.round(summary.helpful_rate * 100)}% helpful` : 'No ratings yet'],
  ], [summary])
  return (
    <div className="paper-grid min-h-[calc(100vh-73px)] px-4 py-10 sm:px-8 lg:px-12">
      <div className="mx-auto max-w-6xl">
        <div className="mb-9">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-ocean">Local research dashboard</p>
          <h1 className="mt-2 font-display text-4xl font-bold">Evaluation overview</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/55">
            These descriptive metrics come from local SQLite traces. Final thesis statistics should be calculated from the locked and blinded evaluation export.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {cards.map(([label, value, Icon, note]) => (
            <div key={label} className="rounded-3xl border border-ink/10 bg-white p-5 shadow-soft">
              <div className="mb-5 grid h-10 w-10 place-items-center rounded-xl bg-mint text-ocean"><Icon size={20} /></div>
              <div className="font-display text-3xl font-bold">{value}</div>
              <div className="mt-1 text-sm font-bold">{label}</div>
              <div className="mt-1 text-xs text-ink/45">{note}</div>
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Breakdown title="Runs by mode" data={summary?.by_mode} labels={{ rag_verified: 'RAG + verification', baseline: 'Plain LLM baseline' }} />
          <Breakdown title="Safety and scope routing" data={summary?.by_intent} labels={{ educational_in_scope: 'Educational, in scope', out_of_scope: 'Out of scope', personal_medical_advice: 'Personal medical advice', emergency: 'Emergency' }} />
        </div>
        <div className="mt-6 rounded-3xl border border-ocean/15 bg-mint/55 p-6">
          <div className="flex gap-4">
            <FlaskConical className="shrink-0 text-ocean" />
            <div>
              <h2 className="font-display text-xl font-bold">3-Layer Triad Verification Protocol</h2>
              <p className="mt-2 text-sm leading-6 text-ink/60">
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
    <div className="rounded-3xl border border-ink/10 bg-white p-6 shadow-soft">
      <h2 className="mb-5 font-display text-xl font-bold">{title}</h2>
      {entries.length ? (
        <div className="space-y-4">
          {entries.map(([key, value]) => (
            <div key={key}>
              <div className="mb-1.5 flex justify-between text-xs">
                <span className="font-semibold">{labels[key] || key}</span>
                <span>{value}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-ink/5">
                <div className="h-full rounded-full bg-ocean" style={{ width: `${(value / total) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid min-h-28 place-items-center rounded-2xl border border-dashed border-ink/15 text-sm text-ink/40">
          No traces recorded yet
        </div>
      )}
    </div>
  )
}
