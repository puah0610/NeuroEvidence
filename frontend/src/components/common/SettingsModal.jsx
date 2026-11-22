import { useEffect, useMemo, useState } from 'react'
import {
  BarChart2,
  Check,
  Database,
  Download,
  FileSpreadsheet,
  HardDrive,
  Moon,
  RotateCcw,
  Settings,
  Sliders,
  Sun,
  Trash2,
  User,
  X,
} from 'lucide-react'
import { DEFAULT_SETTINGS, getDefaultProfileForUser, getStoredSessions, getStoredSettings } from '../../utils/sessionStore'

export default function SettingsModal({
  isOpen,
  onClose,
  userId = 'admin',
  userProfile,
  workspaceSettings,
  onSaveSettings,
  sessionsCount,
  onClearAllSessions,
  onOpenEvaluation,
  isAdmin = false,
}) {
  const [activeTab, setActiveTab] = useState('general')
  const [settings, setSettings] = useState(() => buildInitialSettings(workspaceSettings, userProfile))
  const [savedToast, setSavedToast] = useState(false)

  function buildInitialSettings(currentSettings, currentProfile) {
    const base = currentSettings || getStoredSettings()
    return {
      general: {
        ...DEFAULT_SETTINGS.general,
        ...(base?.general || {}),
      },
      profile: {
        ...DEFAULT_SETTINGS.profile,
        ...(base?.profile || {}),
        ...(currentProfile || {}),
      },
    }
  }

  // Re-sync local form state from saved settings whenever modal opens (discarding cancelled edits)
  useEffect(() => {
    if (isOpen) {
      setSettings(buildInitialSettings(workspaceSettings, userProfile))
      setSavedToast(false)
    }
  }, [isOpen, workspaceSettings, userProfile])

  // Live-preview theme selection while modal is open, and restore saved theme if cancelled
  useEffect(() => {
    if (!isOpen) return
    const root = document.documentElement
    const previewDark = settings.general.theme === 'dark'
    root.classList.toggle('dark', previewDark)
    return () => {
      const savedDark = (workspaceSettings?.general?.theme || 'light') === 'dark'
      root.classList.toggle('dark', savedDark)
    }
  }, [isOpen, settings.general.theme, workspaceSettings?.general?.theme])

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  // Calculate approximate browser localStorage usage
  const storageMetrics = useMemo(() => {
    if (!isOpen) return { kb: '0.0', mb: '0.00', percent: 0, totalBytes: 0 }
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
      return { kb: '0.0', mb: '0.00', percent: 0, totalBytes: 0 }
    }
  }, [isOpen, sessionsCount])

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
    onSaveSettings?.(settings)
    setSavedToast(true)
    setTimeout(() => {
      setSavedToast(false)
      onClose()
    }, 500)
  }

  function handleResetDefaults() {
    if (window.confirm('Reset all workspace settings and profile fields to their defaults?')) {
      const defaults = {
        general: { ...DEFAULT_SETTINGS.general },
        profile: getDefaultProfileForUser(userId),
      }
      setSettings(defaults)
      onSaveSettings?.(defaults)
      setSavedToast(true)
      setTimeout(() => setSavedToast(false), 1200)
    }
  }

  function handleExportJSON() {
    try {
      const userSessions = getStoredSessions(userId)
      const blob = new Blob([JSON.stringify(userSessions, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `neuroevidence_${userId}_sessions_${new Date().toISOString().slice(0, 10)}.json`
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
      const rawSessions = getStoredSessions(userId)
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
      a.download = `neuroevidence_${userId}_sessions_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Failed to export CSV:', e)
    }
  }

  const tabs = [
    { id: 'general', label: 'General & Retrieval', icon: Sliders },
    { id: 'profile', label: 'User Profile', icon: User },
    { id: 'data', label: 'Data & Storage', icon: HardDrive },
  ]

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-xs fade-up"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative flex flex-col w-full max-w-3xl h-[600px] max-h-[90vh] rounded-2xl border border-neutral-200 bg-white shadow-2xl overflow-hidden"
      >
        {/* Top Modal Header */}
        <div className="flex items-center justify-between border-b border-neutral-100 px-6 py-3.5 bg-neutral-50/50 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-neutral-200/80 text-ink">
              <Settings size={18} />
            </div>
            <div>
              <h3 className="font-display text-sm font-bold text-ink">Workspace Settings</h3>
              <p className="text-[11px] text-neutral-400">
                Configure display preferences, live retrieval behavior, user profile, and local data
              </p>
            </div>
          </div>
          <button
            type="button"
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
            {/* GENERAL & RETRIEVAL TAB */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">General & Retrieval Preferences</h4>
                  <p className="text-xs text-neutral-500">
                    Customize chat layout density, navigation helpers, and live PubMed retrieval behavior.
                  </p>
                </div>

                {/* Theme & Appearance */}
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-2">
                    Theme & Appearance
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'light', label: 'Light Mode', icon: Sun },
                      { id: 'dark', label: 'Dark Mode', icon: Moon },
                    ].map((t) => {
                      const Icon = t.icon
                      const selected = (settings.general.theme || 'light') === t.id
                      return (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => updateNested('general', 'theme', t.id)}
                          className={`flex items-center justify-center gap-2 rounded-xl border p-2.5 text-xs font-semibold transition ${
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
                  <label className="block text-xs font-semibold text-neutral-700 mb-2">
                    Chat Display Density
                  </label>
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

                {/* Working Toggles */}
                <div className="space-y-4 pt-3 border-t border-neutral-100">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="text-xs font-semibold text-neutral-700">
                        Auto-Scroll to Latest Message
                      </div>
                      <div className="text-[11px] text-neutral-400">
                        Automatically scroll the chat canvas as new answers arrive
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.general.autoScroll}
                      onChange={(e) => updateNested('general', 'autoScroll', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer shrink-0"
                    />
                  </div>

                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="text-xs font-semibold text-neutral-700">
                        Keyboard Shortcuts Hint
                      </div>
                      <div className="text-[11px] text-neutral-400">
                        Display Enter / Shift+Enter shortcut guide below the chat input
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.general.showShortcuts}
                      onChange={(e) => updateNested('general', 'showShortcuts', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer shrink-0"
                    />
                  </div>

                  <div className="flex items-center justify-between gap-4 rounded-xl border border-cyan-200/70 bg-cyan-50/40 p-3.5">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-neutral-800">
                          Agentic Live PubMed Fallback
                        </span>
                        <span className="rounded bg-cyan-100 px-1.5 py-0.5 text-[9px] font-bold text-cyan-800 uppercase tracking-wide">
                          NCBI Live
                        </span>
                      </div>
                      <div className="text-[11px] text-neutral-500 mt-0.5 leading-relaxed">
                        Automatically query NCBI E-utilities and neural-rerank recent clinical trials when the local Triad corpus lacks Layer 3 empirical evidence.
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.general.enableLivePubMed ?? true}
                      onChange={(e) => updateNested('general', 'enableLivePubMed', e.target.checked)}
                      className="h-4 w-4 rounded accent-ocean cursor-pointer shrink-0"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* USER PROFILE TAB */}
            {activeTab === 'profile' && (
              <div className="space-y-5">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">User Profile</h4>
                  <p className="text-xs text-neutral-500">
                    Stored locally in your browser to personalize your educational workspace identity.
                  </p>
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
                      : 'DP'}
                  </div>
                  <div>
                    <div className="text-xs font-bold text-ink">
                      {settings.profile.name || 'Daniel Puah'}
                    </div>
                    <div className="text-[11px] text-neutral-500">{settings.profile.role}</div>
                    <div className="text-[10px] text-emerald-600 font-semibold mt-0.5 flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      <span>
                        {isAdmin
                          ? 'Admin · Researcher / Developer Account'
                          : 'Clinician · Standard Verified RAG Account'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-neutral-700 mb-1">
                      Display Name
                    </label>
                    <input
                      type="text"
                      value={settings.profile.name}
                      onChange={(e) => updateNested('profile', 'name', e.target.value)}
                      placeholder="e.g. Daniel Puah"
                      className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-neutral-700 mb-1">
                      Role / Title
                    </label>
                    <input
                      type="text"
                      value={settings.profile.role}
                      onChange={(e) => updateNested('profile', 'role', e.target.value)}
                      placeholder="e.g. Medical Student / Researcher"
                      className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Institution / Department
                  </label>
                  <input
                    type="text"
                    value={settings.profile.institution}
                    onChange={(e) => updateNested('profile', 'institution', e.target.value)}
                    placeholder="e.g. School of Medicine / University Health"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Academic Email
                  </label>
                  <input
                    type="email"
                    value={settings.profile.email}
                    onChange={(e) => updateNested('profile', 'email', e.target.value)}
                    placeholder="daniel.puah@university.edu"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Focus Area
                  </label>
                  <input
                    type="text"
                    value={settings.profile.specialty}
                    onChange={(e) => updateNested('profile', 'specialty', e.target.value)}
                    placeholder="e.g. Neurology & Neurotherapeutics"
                    className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-ink outline-none focus:border-ocean focus:bg-white transition"
                  />
                </div>
              </div>
            )}

            {/* DATA & STORAGE TAB */}
            {activeTab === 'data' && (
              <div className="space-y-5">
                <div>
                  <h4 className="text-sm font-bold text-ink mb-1">Data Control & Storage</h4>
                  <p className="text-xs text-neutral-500">
                    Inspect browser storage usage, export chat history, or open the evaluation dashboard.
                  </p>
                </div>

                {/* Storage Meter */}
                <div className="rounded-xl border border-neutral-200 p-4 bg-neutral-50/60 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-neutral-700 flex items-center gap-1.5">
                      <Database size={14} className="text-ocean" />
                      <span>Browser Storage Used</span>
                    </span>
                    <span className="font-mono text-neutral-600 font-bold">
                      {storageMetrics.kb} KB ({storageMetrics.percent}%)
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-neutral-200 overflow-hidden">
                    <div
                      className="h-full bg-ocean rounded-full transition-all duration-300"
                      style={{ width: `${Math.max(3, storageMetrics.percent)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-neutral-400">
                    <span>{sessionsCount || 0} Saved Sessions</span>
                    <span className="font-mono">Server folder: data/users/{userId}/</span>
                  </div>
                </div>

                {/* Export Options */}
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-2">
                    Export Workspace Data
                  </label>
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

                {/* Evaluation Dashboard Shortcut (Admin Only) */}
                {isAdmin && (
                  <div className="rounded-xl border border-neutral-200 p-4 bg-neutral-50/30">
                    <div className="text-xs font-bold text-ink mb-1 flex items-center gap-1.5">
                      <BarChart2 size={14} className="text-ocean" />
                      <span>Research Benchmark Evaluation</span>
                    </div>
                    <p className="text-[11px] text-neutral-500 leading-relaxed mb-2.5">
                      Inspect recorded SQLite trace counts, mode distributions, latency, and feedback metrics.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        onClose()
                        onOpenEvaluation?.()
                      }}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-ocean hover:underline"
                    >
                      <span>Go to Evaluation & Metrics dashboard</span>
                      <span>&rarr;</span>
                    </button>
                  </div>
                )}

                {/* Danger Zone */}
                <div className="pt-3 border-t border-neutral-100 space-y-2">
                  <div className="text-xs font-bold text-red-600">Danger Zone</div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (
                          window.confirm(
                            'Are you sure you want to delete all chat sessions? This cannot be undone.'
                          )
                        ) {
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
