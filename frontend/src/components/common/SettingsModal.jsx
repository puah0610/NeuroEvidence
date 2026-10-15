import { useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  BarChart2,
  Bell,
  Check,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  HardDrive,
  Languages,
  Mic,
  Moon,
  RotateCcw,
  Settings,
  Shield,
  Sliders,
  Sun,
  Trash2,
  User,
  Volume2,
  X,
} from 'lucide-react'
import { DEFAULT_SETTINGS, getStoredSettings, saveStoredSettings } from '../../utils/sessionStore'

export default function SettingsModal({
  isOpen,
  onClose,
  userProfile,
  onSaveProfile,
  sessionsCount,
  onClearAllSessions,
}) {
  const [activeTab, setActiveTab] = useState('general')
  const [settings, setSettings] = useState(() => {
    const stored = getStoredSettings()
    return {
      ...DEFAULT_SETTINGS,
      ...stored,
      profile: {
        ...DEFAULT_SETTINGS.profile,
        ...(userProfile || stored.profile),
      },
    }
  })
  const [savedToast, setSavedToast] = useState(false)

  // Calculate approximate storage used
  const storageMetrics = useMemo(() => {
    try {
      let totalBytes = 0
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        const val = localStorage.getItem(key)
        totalBytes += (key.length + (val ? val.length : 0)) * 2
      }
      const kb = (totalBytes / 1024).toFixed(1)
      const mb = (totalBytes / (1024 * 1024)).toFixed(2)
      const percent = Math.min(100, Math.round((totalBytes / (5 * 1024 * 1024)) * 100))
      return { kb, mb, percent, totalBytes }
    } catch {
      return { kb: '45.2', mb: '0.04', percent: 2, totalBytes: 45000 }
    }
  }, [isOpen])

  if (!isOpen) return null

  function updateNested(section, key, value) {
    setSettings((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value,
      },
    }))
  }

  function handleSave(e) {
    e?.preventDefault()
    saveStoredSettings(settings)
    if (onSaveProfile && settings.profile) {
      onSaveProfile(settings.profile)
    }
    setSavedToast(true)
    setTimeout(() => {
      setSavedToast(false)
      onClose()
    }, 600)
  }

  function handleResetDefaults() {
    if (window.confirm('Reset all workspace settings to their initial clinical defaults?')) {
      setSettings(DEFAULT_SETTINGS)
      saveStoredSettings(DEFAULT_SETTINGS)
      if (onSaveProfile) {
        onSaveProfile(DEFAULT_SETTINGS.profile)
      }
      setSavedToast(true)
      setTimeout(() => setSavedToast(false), 1200)
    }
  }

  function handleExportJSON() {
    try {
      const rawSessions = localStorage.getItem('neuroevidence_sessions_v1') || '[]'
      const blob = new Blob([rawSessions], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `neuroevidence_sessions_${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Failed to export sessions:', e)
    }
  }

  function handleExportCSV() {
    try {
      const rawSessions = JSON.parse(localStorage.getItem('neuroevidence_sessions_v1') || '[]')
      const headers = ['id', 'title', 'folderId', 'timestamp', 'messageCount']
      const rows = rawSessions.map((s) => [
        s.id,
        `"${(s.title || '').replace(/"/g, '""')}"`,
        s.folderId || 'f-general',
        s.timestamp ? new Date(s.timestamp).toISOString() : '',
        s.messages?.length || 0,
      ])
      const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `neuroevidence_manifest_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Failed to export CSV:', e)
    }
  }

  const tabs = [
    { id: 'general', label: 'General', icon: Sliders },
    { id: 'profile', label: 'Clinician Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'voice', label: 'Voice & Audio', icon: Volume2 },
    { id: 'analytics', label: 'Analytics & Research', icon: Activity },
    { id: 'data', label: 'Data & Storage', icon: HardDrive },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-xs fade-up">
      <div className="relative flex flex-col w-full max-w-3xl h-[650px] max-h-[90vh] rounded-2xl border border-neutral-200 bg-white shadow-2xl overflow-hidden">
        {/* Top Modal Header */}
        <div className="flex items-center justify-between border-b border-neutral-100 px-6 py-3.5 bg-neutral-50/50 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-neutral-200/80 text-ink">
              <Settings size={18} />
            </div>
            <div>
              <h3 className="font-display text-sm font-bold text-ink">Workspace Settings</h3>
              <p className="text-[11px] text-neutral-400">Configure appearance, clinician profile, voice, alerts, and data</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-200/60 hover:text-ink transition"
            aria-label="Close settings"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body: Left Vertical Sidebar + Right Content Pane */}
        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Settings Left Tab Menu */}
          <div className="w-52 border-r border-neutral-100 bg-[#fafafa] p-3 space-y-1 shrink-0 overflow-y-auto">
            <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
              Preferences
            </div>
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold transition ${
                    isActive
                      ? 'bg-ink text-white shadow-xs'
                      : 'text-neutral-600 hover:bg-neutral-200/60 hover:text-ink'
                  }`}
                >
                  <Icon size={15} className={isActive ? 'text-white' : 'text-neutral-400'} />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>

          {/* Settings Right Form Pane */}
          <div className="flex-1 overflow-y-auto p-6 bg-white">
            {/* GENERAL TAB */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">General Preferences</h4>
                  <p className="text-xs text-neutral-500">Configure visual appearance and workspace interface behavior.</p>
                </div>

                {/* Theme / Appearance */}
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-2">Theme & Appearance</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'light', label: 'Light', icon: Sun },
                      { id: 'dark', label: 'Dark (Beta)', icon: Moon },
                      { id: 'system', label: 'Match System', icon: Sliders },
                    ].map((t) => {
                      const Icon = t.icon
                      const selected = settings.general.theme === t.id
                      return (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => updateNested('general', 'theme', t.id)}
                          className={`flex items-center justify-center gap-2 rounded-xl border p-3 text-xs font-semibold transition ${
                            selected
                              ? 'border-ocean bg-ocean/5 text-ocean ring-1 ring-ocean'
                              : 'border-neutral-200 hover:bg-neutral-50 text-neutral-600'
                          }`}
                        >
                          <Icon size={15} />
                          <span>{t.label}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Display Density */}
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-2">Chat Display Density</label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'default', label: 'Comfortable (Standard)' },
                      { id: 'compact', label: 'Compact (High Density)' },
                    ].map((d) => {
                      const selected = settings.general.density === d.id
                      return (
                        <button
                          key={d.id}
                          type="button"
                          onClick={() => updateNested('general', 'density', d.id)}
                          className={`rounded-xl border p-2.5 text-xs font-medium text-center transition ${
                            selected
                              ? 'border-ocean bg-ocean/5 text-ocean font-semibold ring-1 ring-ocean'
                              : 'border-neutral-200 hover:bg-neutral-50 text-neutral-600'
                          }`}
                        >
                          {d.label}
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Toggles */}
                <div className="space-y-3 pt-2 border-t border-neutral-100">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-neutral-700">Auto-Scroll During Stream</div>
                      <div className="text-[11px] text-neutral-400">Keep latest assistant reasoning tokens in view</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.general.autoScroll}
                      onChange={(e) => updateNested('general', 'autoScroll', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-neutral-700">Keyboard Shortcuts Hint</div>
                      <div className="text-[11px] text-neutral-400">Show helpful shortcut badges (e.g. Enter to send, Shift+Enter)</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.general.showShortcuts}
                      onChange={(e) => updateNested('general', 'showShortcuts', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-neutral-700">Agentic Live PubMed Fallback</span>
                        <span className="rounded bg-cyan-100 px-1.5 py-0.5 text-[9px] font-bold text-cyan-800 uppercase tracking-wide">
                          NCBI Live
                        </span>
                      </div>
                      <div className="text-[11px] text-neutral-400">
                        Automatically query NCBI E-utilities & neural-rerank clinical trials when local corpus lacks empirical evidence
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.general.enableLivePubMed ?? true}
                      onChange={(e) => updateNested('general', 'enableLivePubMed', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer"
                    />
                  </div>
                </div>

                {/* Language */}
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1.5">Workspace Language</label>
                  <select
                    value={settings.general.language}
                    onChange={(e) => updateNested('general', 'language', e.target.value)}
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  >
                    <option value="en-US">English (United States)</option>
                    <option value="en-GB">English (United Kingdom)</option>
                    <option value="en-SG">English (Singapore)</option>
                  </select>
                </div>
              </div>
            )}

            {/* CLINICIAN PROFILE TAB */}
            {activeTab === 'profile' && (
              <div className="space-y-5">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">Clinician Profile</h4>
                  <p className="text-xs text-neutral-500">Your profile details are stored locally and customize your workspace identity.</p>
                </div>

                <div className="flex items-center gap-4 p-3.5 rounded-xl bg-neutral-50 border border-neutral-100">
                  <div className="grid h-12 w-12 place-items-center rounded-2xl bg-ocean text-white font-bold text-sm shadow-xs">
                    {settings.profile.name
                      ? settings.profile.name
                          .split(' ')
                          .map((n) => n[0])
                          .join('')
                          .slice(0, 2)
                          .toUpperCase()
                      : 'DR'}
                  </div>
                  <div>
                    <div className="text-xs font-bold text-ink">{settings.profile.name || 'Dr. Daniel'}</div>
                    <div className="text-[11px] text-neutral-500">{settings.profile.role}</div>
                    <div className="text-[10px] text-emerald-600 font-semibold mt-0.5 flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      <span>Clinician Verified</span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-neutral-700 mb-1">Display Name</label>
                    <input
                      type="text"
                      value={settings.profile.name}
                      onChange={(e) => updateNested('profile', 'name', e.target.value)}
                      placeholder="e.g. Dr. Daniel Puah"
                      className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-neutral-700 mb-1">Role / Title</label>
                    <input
                      type="text"
                      value={settings.profile.role}
                      onChange={(e) => updateNested('profile', 'role', e.target.value)}
                      placeholder="e.g. Clinical Neurologist"
                      className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">Healthcare Institution / Clinic</label>
                  <input
                    type="text"
                    value={settings.profile.institution}
                    onChange={(e) => updateNested('profile', 'institution', e.target.value)}
                    placeholder="e.g. Movement Disorders & Neurotherapeutics Center"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">Institutional Email</label>
                  <input
                    type="email"
                    value={settings.profile.email}
                    onChange={(e) => updateNested('profile', 'email', e.target.value)}
                    placeholder="daniel.puah@clinical.org"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">Specialty Subfield</label>
                  <input
                    type="text"
                    value={settings.profile.specialty}
                    onChange={(e) => updateNested('profile', 'specialty', e.target.value)}
                    placeholder="e.g. Movement Disorders & Epilepsy"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>
              </div>
            )}

            {/* NOTIFICATIONS TAB */}
            {activeTab === 'notifications' && (
              <div className="space-y-5">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">Notifications & Clinical Alerts</h4>
                  <p className="text-xs text-neutral-500">Configure notification alerts for contraindications, evidence updates, and digests.</p>
                </div>

                <div className="space-y-4">
                  <div className="flex items-start justify-between rounded-xl border border-neutral-200 p-3.5 bg-neutral-50/50">
                    <div className="pr-4">
                      <div className="text-xs font-semibold text-ink flex items-center gap-1.5">
                        <AlertTriangle size={14} className="text-amber-500" />
                        <span>Critical Safety & Drug Contraindication Alerts</span>
                      </div>
                      <div className="text-[11px] text-neutral-500 mt-1 leading-relaxed">
                        Immediately highlight high-risk drug-drug interactions (e.g. MAO-B + SSRI serotonin syndrome warnings).
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.notifications.safetyAlerts}
                      onChange={(e) => updateNested('notifications', 'safetyAlerts', e.target.checked)}
                      className="mt-1 h-4 w-4 rounded accent-ocean cursor-pointer shrink-0"
                    />
                  </div>

                  <div className="flex items-start justify-between rounded-xl border border-neutral-200 p-3.5 bg-neutral-50/50">
                    <div className="pr-4">
                      <div className="text-xs font-semibold text-ink flex items-center gap-1.5">
                        <Bell size={14} className="text-ocean" />
                        <span>Triad Knowledge Base Ingestion Updates</span>
                      </div>
                      <div className="text-[11px] text-neutral-500 mt-1 leading-relaxed">
                        Notify when newer clinical practice guidelines or Cochrane trials are indexed into the local manifest.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.notifications.triadUpdates}
                      onChange={(e) => updateNested('notifications', 'triadUpdates', e.target.checked)}
                      className="mt-1 h-4 w-4 rounded accent-ocean cursor-pointer shrink-0"
                    />
                  </div>

                  <div className="flex items-start justify-between rounded-xl border border-neutral-200 p-3.5 bg-neutral-50/50">
                    <div className="pr-4">
                      <div className="text-xs font-semibold text-ink flex items-center gap-1.5">
                        <Volume2 size={14} className="text-neutral-500" />
                        <span>Audio Completion Chime</span>
                      </div>
                      <div className="text-[11px] text-neutral-500 mt-1 leading-relaxed">
                        Play a subtle clinical chime when background multi-step reasoning completes.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.notifications.soundAlerts}
                      onChange={(e) => updateNested('notifications', 'soundAlerts', e.target.checked)}
                      className="mt-1 h-4 w-4 rounded accent-ocean cursor-pointer shrink-0"
                    />
                  </div>

                  <div className="flex items-start justify-between rounded-xl border border-neutral-200 p-3.5 bg-neutral-50/50">
                    <div className="pr-4">
                      <div className="text-xs font-semibold text-ink flex items-center gap-1.5">
                        <FileText size={14} className="text-neutral-500" />
                        <span>Weekly Research Query Digest</span>
                      </div>
                      <div className="text-[11px] text-neutral-500 mt-1 leading-relaxed">
                        Summarize recurring clinical questions and evidence-verified consensus in a weekly briefing.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.notifications.emailDigest}
                      onChange={(e) => updateNested('notifications', 'emailDigest', e.target.checked)}
                      className="mt-1 h-4 w-4 rounded accent-ocean cursor-pointer shrink-0"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* VOICE & AUDIO TAB */}
            {activeTab === 'voice' && (
              <div className="space-y-5">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">Voice & Audio Settings</h4>
                  <p className="text-xs text-neutral-500">Dictate clinical inquiries hands-free and configure audio playback voices.</p>
                </div>

                <div className="flex items-center justify-between rounded-xl border border-neutral-200 p-3.5 bg-neutral-50/50">
                  <div className="pr-4">
                    <div className="text-xs font-semibold text-ink flex items-center gap-1.5">
                      <Mic size={14} className="text-ocean" />
                      <span>Speech-to-Text Clinical Dictation</span>
                    </div>
                    <div className="text-[11px] text-neutral-500 mt-1">
                      Enables microphone input for hands-free clinical question dictation in the chat input.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.voice.voiceInput}
                    onChange={(e) => updateNested('voice', 'voiceInput', e.target.checked)}
                    className="h-4 w-4 rounded accent-ocean cursor-pointer shrink-0"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1.5">Assistant TTS Voice</label>
                  <select
                    value={settings.voice.ttsVoice}
                    onChange={(e) => updateNested('voice', 'ttsVoice', e.target.value)}
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  >
                    <option value="nova">Nova (Natural Clinical Tone - Recommended)</option>
                    <option value="alloy">Alloy (Balanced Neutral)</option>
                    <option value="echo">Echo (Warm Conversational)</option>
                    <option value="onyx">Onyx (Authoritative Deep)</option>
                  </select>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-semibold text-neutral-700">Audio Playback Speed</label>
                    <span className="text-xs font-bold text-ocean">{settings.voice.speechRate}x</span>
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    {['0.8', '1.0', '1.25', '1.5'].map((rate) => {
                      const selected = settings.voice.speechRate === rate
                      return (
                        <button
                          key={rate}
                          type="button"
                          onClick={() => updateNested('voice', 'speechRate', rate)}
                          className={`rounded-xl border p-2 text-xs font-medium text-center transition ${
                            selected
                              ? 'border-ocean bg-ocean/5 text-ocean font-bold ring-1 ring-ocean'
                              : 'border-neutral-200 hover:bg-neutral-50 text-neutral-600'
                          }`}
                        >
                          {rate}x
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-neutral-100">
                  <div>
                    <div className="text-xs font-semibold text-neutral-700">Auto-Read Answers Aloud</div>
                    <div className="text-[11px] text-neutral-400">Automatically speak the direct 2-sentence clinical answer</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.voice.autoRead}
                    onChange={(e) => updateNested('voice', 'autoRead', e.target.checked)}
                    className="h-4 w-4 rounded accent-ocean cursor-pointer"
                  />
                </div>
              </div>
            )}

            {/* ANALYTICS & RESEARCH TAB */}
            {activeTab === 'analytics' && (
              <div className="space-y-5">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">Analytics & Research Telemetry</h4>
                  <p className="text-xs text-neutral-500">Track response latencies, evaluation score distributions, and local traces.</p>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between rounded-xl border border-neutral-200 p-3.5 bg-neutral-50/50">
                    <div>
                      <div className="text-xs font-semibold text-ink">Record Local Evaluation Traces</div>
                      <div className="text-[11px] text-neutral-500 mt-0.5">
                        Log inference latency, input/output tokens, and claim verification outcomes to local SQLite.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.analytics.recordTraces}
                      onChange={(e) => updateNested('analytics', 'recordTraces', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer shrink-0 ml-4"
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-neutral-200 p-3.5 bg-neutral-50/50">
                    <div>
                      <div className="text-xs font-semibold text-ink">Response Latency Profiling</div>
                      <div className="text-[11px] text-neutral-500 mt-0.5">
                        Display retrieval time vs generation time breakdowns in evidence cards.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.analytics.latencyTracking}
                      onChange={(e) => updateNested('analytics', 'latencyTracking', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer shrink-0 ml-4"
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-neutral-200 p-3.5 bg-neutral-50/50">
                    <div>
                      <div className="text-xs font-semibold text-ink">Anonymized Evidence Citations Metrics</div>
                      <div className="text-[11px] text-neutral-500 mt-0.5">
                        Aggregate citation coverage across Layer 1 (StatPearls), Layer 2 (Guidelines), and Layer 3 (Trials).
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.analytics.anonymizedTelemetry}
                      onChange={(e) => updateNested('analytics', 'anonymizedTelemetry', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer shrink-0 ml-4"
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-neutral-200 p-4 bg-neutral-50/30">
                  <div className="text-xs font-bold text-ink mb-1 flex items-center gap-1.5">
                    <BarChart2 size={14} className="text-ocean" />
                    <span>Research Benchmark Evaluation</span>
                  </div>
                  <p className="text-[11px] text-neutral-500 leading-relaxed mb-3">
                    View complete descriptive statistics and blinded evaluation exports in the Evaluation dashboard.
                  </p>
                  <a
                    href="#evaluation"
                    onClick={(e) => {
                      e.preventDefault()
                      onClose()
                      window.location.hash = 'evaluation'
                    }}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-ocean hover:underline"
                  >
                    <span>Go to Evaluation & Metrics dashboard</span>
                    <span>&rarr;</span>
                  </a>
                </div>
              </div>
            )}

            {/* DATA & STORAGE TAB */}
            {activeTab === 'data' && (
              <div className="space-y-5">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">Data Control & Storage</h4>
                  <p className="text-xs text-neutral-500">Manage local browser cache, export chat sessions, and configure data retention.</p>
                </div>

                {/* Storage Meter */}
                <div className="rounded-xl border border-neutral-200 p-4 bg-neutral-50/60 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-neutral-700 flex items-center gap-1.5">
                      <Database size={14} className="text-ocean" />
                      <span>Browser Storage Used</span>
                    </span>
                    <span className="font-mono text-neutral-600 font-bold">{storageMetrics.kb} KB ({storageMetrics.percent}%)</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-neutral-200 overflow-hidden">
                    <div
                      className="h-full bg-ocean rounded-full transition-all duration-300"
                      style={{ width: `${Math.max(3, storageMetrics.percent)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-neutral-400">
                    <span>{sessionsCount || 0} Saved Sessions</span>
                    <span>Max quota: 5.0 MB localStorage</span>
                  </div>
                </div>

                {/* Export Options */}
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-2">Export Workspace Data</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={handleExportJSON}
                      className="flex items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-white p-2.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300 transition shadow-2xs"
                    >
                      <Download size={14} className="text-ocean" />
                      <span>Export JSON (Full History)</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleExportCSV}
                      className="flex items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-white p-2.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300 transition shadow-2xs"
                    >
                      <FileSpreadsheet size={14} className="text-emerald-600" />
                      <span>Export CSV (Manifest)</span>
                    </button>
                  </div>
                </div>

                {/* Auto Delete / Retention */}
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1.5">Chat Session Retention Policy</label>
                  <select
                    value={settings.storage.retention}
                    onChange={(e) => updateNested('storage', 'retention', e.target.value)}
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  >
                    <option value="never">Never auto-delete (Keep forever locally)</option>
                    <option value="30days">Auto-delete sessions older than 30 days</option>
                    <option value="90days">Auto-delete sessions older than 90 days</option>
                    <option value="1year">Auto-delete sessions older than 1 year</option>
                  </select>
                </div>

                {/* Danger Zone */}
                <div className="pt-3 border-t border-neutral-100 space-y-2">
                  <div className="text-xs font-bold text-red-600">Danger Zone</div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (window.confirm('Are you sure you want to delete all chat sessions? This cannot be undone.')) {
                          onClearAllSessions()
                          onClose()
                        }
                      }}
                      className="flex-1 flex items-center justify-center gap-1.5 rounded-xl border border-red-200 bg-red-50/60 p-2.5 text-xs font-semibold text-red-600 hover:bg-red-100 transition"
                    >
                      <Trash2 size={13} />
                      <span>Clear All Sessions</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleResetDefaults}
                      className="flex items-center justify-center gap-1.5 rounded-xl border border-neutral-200 bg-neutral-50 p-2.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100 transition"
                      title="Reset settings to defaults"
                    >
                      <RotateCcw size={13} />
                      <span>Reset Defaults</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Bottom Footer */}
        <div className="flex items-center justify-between border-t border-neutral-100 px-6 py-3.5 bg-neutral-50/50 shrink-0">
          <div className="text-[11px] text-neutral-400">
            {savedToast ? (
              <span className="flex items-center gap-1.5 text-emerald-600 font-semibold">
                <Check size={14} /> Settings saved successfully!
              </span>
            ) : (
              'All settings persist locally in your browser'
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-xs font-semibold text-neutral-600 hover:bg-neutral-50 transition shadow-2xs"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="rounded-xl bg-ink px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-ocean transition"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
