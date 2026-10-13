import { BookOpen, FlaskConical, Layers, ShieldCheck, X } from 'lucide-react'

export default function TriadModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-xs fade-up">
      <div className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-neutral-200 bg-white p-6 shadow-2xl sm:p-8">
        <div className="flex items-center justify-between border-b border-neutral-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-mint text-ocean">
              <Layers size={22} />
            </div>
            <div>
              <h2 className="font-display text-xl font-bold text-ink">The 3-Layer Triad Knowledge Base</h2>
              <p className="text-xs text-neutral-500">Parkinson's Disease and Epilepsy Architecture</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl p-2 text-neutral-400 hover:bg-neutral-100 hover:text-ink transition"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        <div className="mt-6 space-y-4">
          {/* Layer 1 */}
          <div className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-5">
            <div className="mb-2 flex items-center gap-2 font-bold text-indigo-900">
              <BookOpen size={18} />
              <span>Layer 1: Foundational Knowledge (NCBI Bookshelf / StatPearls)</span>
            </div>
            <div className="grid gap-3 text-xs text-indigo-950 sm:grid-cols-2">
              <div className="rounded-xl border border-indigo-100 bg-white p-3.5 shadow-xs">
                <span className="mb-1 block font-bold">Epilepsy</span>
                • ILAE 2017 Seizure & Epilepsy Classification<br />
                • Seizure Semiology & Cortical Hypersynchrony<br />
                • Anti-seizure Medication (ASM) Cellular Targets
              </div>
              <div className="rounded-xl border border-indigo-100 bg-white p-3.5 shadow-xs">
                <span className="mb-1 block font-bold">Parkinson's Disease</span>
                • SNpc Dopaminergic Loss & Alpha-Synuclein Pathology<br />
                • Hoehn and Yahr Clinical Staging (Stages 1–5)<br />
                • Core Pharmacology (Levodopa/Carbidopa, Agonists, MAO-B)
              </div>
            </div>
          </div>

          {/* Layer 2 */}
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/40 p-5">
            <div className="mb-2 flex items-center gap-2 font-bold text-emerald-900">
              <ShieldCheck size={18} />
              <span>Layer 2: Clinical Guidelines & Consensus (NICE Guidelines)</span>
            </div>
            <div className="grid gap-3 text-xs text-emerald-950 sm:grid-cols-2">
              <div className="rounded-xl border border-emerald-100 bg-white p-3.5 shadow-xs">
                <span className="mb-1 block font-bold">NICE NG217 (Epilepsies)</span>
                • First Seizure Presentation (Specialist review &lt;2 weeks)<br />
                • Monotherapy Algorithms (Focal vs Generalized)<br />
                • Teratogenicity & Valproate Pregnancy Prevention (Prevent)
              </div>
              <div className="rounded-xl border border-emerald-100 bg-white p-3.5 shadow-xs">
                <span className="mb-1 block font-bold">NICE NG71 (Parkinson's)</span>
                • Specialist Diagnosis (UK Brain Bank Criteria)<br />
                • First-Line Treatment Stratified by Quality of Life<br />
                • Motor Fluctuation Management & Advanced Care (DBS)
              </div>
            </div>
          </div>

          {/* Layer 3 */}
          <div className="rounded-2xl border border-purple-200 bg-purple-50/40 p-5">
            <div className="mb-2 flex items-center gap-2 font-bold text-purple-900">
              <FlaskConical size={18} />
              <span>Layer 3: Empirical Evidence & Trials (PubMed Central / Cochrane)</span>
            </div>
            <div className="grid gap-3 text-xs text-purple-950 sm:grid-cols-2">
              <div className="rounded-xl border border-purple-100 bg-white p-3.5 shadow-xs">
                <span className="mb-1 block font-bold">Comparative RCTs (SANAD II)</span>
                • Generalized Arm: Levetiracetam vs Valproate (Lancet 2021)<br />
                • Focal Arm: Levetiracetam vs Lamotrigine (Lancet 2021)<br />
                • Long-term remission, treatment retention & safety trade-offs
              </div>
              <div className="rounded-xl border border-purple-100 bg-white p-3.5 shadow-xs">
                <span className="mb-1 block font-bold">Systematic Reviews & Meta-Analyses</span>
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
