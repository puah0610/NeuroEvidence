import {
  ArrowUpRight,
  BookOpen,
  FlaskConical,
  Layers,
  Pill,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'

export default function KnowledgeBoard({
  activeWorkspace,
  onSelectQuery,
  onOpenTriad,
}) {
  // Clinical inquiries organized by topic
  const inquiries = [
    {
      id: 'q1',
      topic: 'epilepsy',
      title: 'NICE NG217 Monotherapy Algorithms',
      description: 'First-line treatment pathways for newly diagnosed focal vs generalized seizures in adults and children.',
      tags: ['Epilepsy', 'NICE NG217', 'Monotherapy'],
      query: 'What does NICE NG217 recommend for first-line treatment of focal vs generalized seizures?',
    },
    {
      id: 'q2',
      topic: 'epilepsy',
      title: 'Sodium Valproate & Lamotrigine Synergy',
      description: 'Glucuronidation inhibition mechanism, titration risks, and Stevens-Johnson syndrome mitigation protocols.',
      tags: ['DDI', 'Valproate', 'Lamotrigine', 'Safety'],
      query: 'Can a patient on sodium valproate be safely started on lamotrigine for focal seizures?',
    },
    {
      id: 'q3',
      topic: 'parkinsons',
      title: 'Hoehn & Yahr Staging & Pharmacotherapy',
      description: 'Levodopa vs dopamine agonists stratification based on motor disability severity and patient quality of life.',
      tags: ['Parkinsons', 'NICE NG71', 'Hoehn & Yahr'],
      query: "How do Hoehn & Yahr staging and NICE NG71 guide levodopa vs dopamine agonists in Parkinson's?",
    },
    {
      id: 'q4',
      topic: 'parkinsons',
      title: 'Metoclopramide & Levodopa Contraindication',
      description: 'Central dopamine D2 receptor antagonism exacerbating parkinsonian symptoms and acute extrapyramidal reactions.',
      tags: ['Contraindication', 'D2 Antagonist', 'Parkinsons'],
      query: 'Why is metoclopramide strictly contraindicated in patients receiving levodopa therapy?',
    },
  ]

  // Triad Layers overview cards
  const triadLayers = [
    {
      layer: 1,
      name: 'Layer 1: Foundational Knowledge',
      source: 'NCBI Bookshelf / StatPearls',
      icon: BookOpen,
      border: 'border-indigo-200/80',
      badge: 'bg-indigo-50 text-indigo-800 border-indigo-200',
      summary: 'Pathophysiology of substantia nigra dopaminergic loss, alpha-synuclein accumulation, and seizure semiology.',
      tags: ['StatPearls', 'ILAE 2017', 'Pathophysiology'],
    },
    {
      layer: 2,
      name: 'Layer 2: Clinical Guidelines',
      source: 'NICE NG217 & NG71',
      icon: ShieldCheck,
      border: 'border-emerald-200/80',
      badge: 'bg-emerald-50 text-emerald-800 border-emerald-200',
      summary: 'Evidence-based clinical guidelines for specialist referrals, first-line drug selection, and motor fluctuations.',
      tags: ['NICE NG217', 'NICE NG71', 'UK Brain Bank'],
    },
    {
      layer: 3,
      name: 'Layer 3: Empirical Trials',
      source: 'PubMed Central & Cochrane',
      icon: FlaskConical,
      border: 'border-purple-200/80',
      badge: 'bg-purple-50 text-purple-800 border-purple-200',
      summary: 'SANAD II randomized comparative trials in Lancet 2021 and Cochrane systematic reviews on DBS outcomes.',
      tags: ['SANAD II', 'Cochrane', 'Lancet 2021'],
    },
  ]

  // Clinical guidance & safety pillars
  const safetyCards = [
    {
      title: 'Pregnancy Prevention (Prevent)',
      category: 'Valproate Safety',
      summary: 'Strict regulatory mandate for women of childbearing potential due to high neurodevelopmental and congenital risks.',
      tags: ['Teratogenicity', 'MHRA / NICE', 'High Alert'],
      icon: ShieldAlert,
      query: 'Explain the safety requirements and alternatives for sodium valproate in women of childbearing potential under NICE NG217.',
    },
    {
      title: 'Dopaminergic Antagonism Advisory',
      category: 'Drug Interaction',
      summary: 'D2 receptor blockers like haloperidol and metoclopramide precipitously worsen motor function in Parkinson patients.',
      tags: ['DDI Check', 'Motor Crisis', 'Contraindicated'],
      icon: Pill,
      query: 'What antiemetic drugs can be safely used in Parkinson disease without worsening motor symptoms?',
    },
  ]

  // Filter items if a specific workspace topic is active
  const filteredInquiries =
    activeWorkspace === 'all'
      ? inquiries
      : inquiries.filter((q) => q.topic === activeWorkspace || activeWorkspace === 'all')

  return (
    <div className="h-full overflow-y-auto p-6 lg:p-8">
      {/* Workspace Banner */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-neutral-200/60 pb-5">
        <div>
          <h2 className="font-display text-xl font-bold text-ink">
            {activeWorkspace === 'parkinsons'
              ? "Parkinson's Disease Knowledge Board"
              : activeWorkspace === 'epilepsy'
              ? 'Epilepsy & Seizures Knowledge Board'
              : 'Clinical Knowledge & Inquiries'}
          </h2>
          <p className="mt-1 text-xs text-neutral-500">
            Curated evidence triad across NCBI Bookshelf, NICE Guidelines, and PMC Clinical Trials.
          </p>
        </div>
        <button
          onClick={onOpenTriad}
          className="flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 shadow-2xs transition hover:border-ocean/40 hover:bg-neutral-50"
        >
          <Layers size={14} className="text-ocean" />
          <span>Inspect Triad Schema</span>
        </button>
      </div>

      {/* 3-Column Clean Board matching the reference */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        {/* Column 1: Clinical Inquiries */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-ocean" />
              <span className="text-xs font-bold text-neutral-800">Clinical Inquiries</span>
              <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-bold text-neutral-500">
                {filteredInquiries.length}
              </span>
            </div>
          </div>

          <div className="space-y-3">
            {filteredInquiries.map((item) => (
              <div
                key={item.id}
                onClick={() => onSelectQuery(item.query)}
                className="group cursor-pointer rounded-2xl border border-neutral-200/80 bg-white p-4 shadow-2xs transition-all duration-150 hover:-translate-y-0.5 hover:border-ocean/40 hover:shadow-sm"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-ink group-hover:text-ocean transition">
                    {item.title}
                  </h3>
                  <ArrowUpRight
                    size={16}
                    className="shrink-0 text-neutral-300 transition group-hover:text-ocean group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                  />
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-neutral-500 line-clamp-2">
                  {item.description}
                </p>
                <div className="mt-3.5 flex flex-wrap gap-1.5">
                  {item.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-md bg-neutral-100/80 px-2 py-0.5 text-[10px] font-medium text-neutral-600"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Column 2: 3-Layer Triad Knowledge */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-indigo-500" />
              <span className="text-xs font-bold text-neutral-800">Evidence Triad</span>
              <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-bold text-neutral-500">
                {triadLayers.length}
              </span>
            </div>
          </div>

          <div className="space-y-3">
            {triadLayers.map((layer) => {
              const Icon = layer.icon
              return (
                <div
                  key={layer.layer}
                  onClick={onOpenTriad}
                  className="group cursor-pointer rounded-2xl border border-neutral-200/80 bg-white p-4 shadow-2xs transition-all duration-150 hover:-translate-y-0.5 hover:border-ocean/40 hover:shadow-sm"
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span
                      className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold border ${layer.badge}`}
                    >
                      <Icon size={11} /> L{layer.layer}
                    </span>
                    <span className="text-[11px] font-medium text-neutral-400 truncate">
                      {layer.source}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-ink group-hover:text-ocean transition">
                    {layer.name}
                  </h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-neutral-500 line-clamp-2">
                    {layer.summary}
                  </p>
                  <div className="mt-3.5 flex flex-wrap gap-1.5">
                    {layer.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-md bg-neutral-100/80 px-2 py-0.5 text-[10px] font-medium text-neutral-600"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Column 3: Safety & Clinical Guidance */}
        <div className="flex flex-col space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-coral" />
              <span className="text-xs font-bold text-neutral-800">Safety & Guidance</span>
              <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-bold text-neutral-500">
                {safetyCards.length}
              </span>
            </div>
          </div>

          <div className="space-y-3">
            {safetyCards.map((safety, idx) => {
              const Icon = safety.icon
              return (
                <div
                  key={idx}
                  onClick={() => onSelectQuery(safety.query)}
                  className="group cursor-pointer rounded-2xl border border-neutral-200/80 bg-white p-4 shadow-2xs transition-all duration-150 hover:-translate-y-0.5 hover:border-coral/40 hover:shadow-sm"
                >
                  <div className="flex items-center gap-1.5 mb-1.5 text-coral text-xs font-semibold">
                    <Icon size={14} />
                    <span>{safety.category}</span>
                  </div>
                  <h3 className="text-sm font-semibold text-ink group-hover:text-coral transition">
                    {safety.title}
                  </h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-neutral-500 line-clamp-2">
                    {safety.summary}
                  </p>
                  <div className="mt-3.5 flex flex-wrap gap-1.5">
                    {safety.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-md bg-neutral-100/80 px-2 py-0.5 text-[10px] font-medium text-neutral-600"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
