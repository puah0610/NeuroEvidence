import { useState } from 'react'
import { Brain, CheckCircle2, LogIn, ShieldAlert } from 'lucide-react'

export default function AuthModal({ isOpen, onClose, onLogin, userProfile }) {
  const [selectedUser, setSelectedUser] = useState(userProfile?.name || 'Dr. Daniel')
  const [loggingIn, setLoggingIn] = useState(false)

  if (!isOpen) return null

  function handleSignIn(e) {
    e.preventDefault()
    setLoggingIn(true)
    setTimeout(() => {
      setLoggingIn(false)
      onLogin()
      onClose()
    }, 400)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4 backdrop-blur-sm fade-up">
      <div className="relative w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
        <div className="text-center mb-6">
          <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-ink text-white shadow-md">
            <Brain size={26} strokeWidth={2} />
          </div>
          <h2 className="font-display text-xl font-bold text-ink">Clinical Workspace</h2>
          <p className="mt-1 text-xs text-neutral-500">
            Sign in to access evidence-verified neurological decision-support
          </p>
        </div>

        <form onSubmit={handleSignIn} className="space-y-4">
          <div className="rounded-xl border border-neutral-200 bg-neutral-50/80 p-3.5 space-y-2">
            <div className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">
              Select Clinician Account
            </div>

            <div
              onClick={() => setSelectedUser(userProfile?.name || 'Dr. Daniel')}
              className="flex cursor-pointer items-center justify-between rounded-xl border border-ocean/30 bg-white p-3 shadow-2xs hover:border-ocean transition"
            >
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-ocean text-white font-bold text-xs shadow-2xs">
                  {userProfile?.name ? userProfile.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase() : 'DP'}
                </div>
                <div>
                  <div className="text-xs font-bold text-ink">{userProfile?.name || 'Dr. Daniel'}</div>
                  <div className="text-[11px] text-neutral-600 font-medium">{userProfile?.role || 'Medical Student / Researcher'}</div>
                  <div className="text-[10px] text-neutral-400 mt-0.5">{userProfile?.specialty || 'Neurology & Neurotherapeutics'}</div>
                </div>
              </div>
              <CheckCircle2 size={18} className="text-ocean" />
            </div>
          </div>

          <div className="rounded-xl border border-amber-200/80 bg-amber-50/70 p-3 text-[11px] text-amber-900 flex items-start gap-2">
            <ShieldAlert size={14} className="shrink-0 text-amber-600 mt-0.5" />
            <span><strong>Educational & Research Use Only:</strong> Grounded in peer-reviewed guidelines and RCTs to assist medical learners. Not for clinical prescribing.</span>
          </div>

          <button
            type="submit"
            disabled={loggingIn}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-ocean transition disabled:opacity-50"
          >
            <LogIn size={15} />
            <span>{loggingIn ? 'Authenticating...' : `Sign In as ${userProfile?.name || 'Daniel Puah'}`}</span>
          </button>
        </form>
      </div>
    </div>
  )
}
