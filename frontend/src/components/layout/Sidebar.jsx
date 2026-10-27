import { useEffect, useRef, useState } from 'react'
import {
  BarChart3,
  Check,
  ChevronDown,
  ChevronRight,
  Cloud,
  Cpu,
  FlaskConical,
  Folder,
  FolderInput,
  FolderPlus,
  HeartPulse,
  LogOut,
  MessageSquare,
  MessageSquarePlus,
  PanelLeftClose,
  Plus,
  Settings,
  ShieldCheck,
  Trash2,
  User,
} from 'lucide-react'
import { formatSessionTimestamp } from '../../utils/sessionStore'

export default function Sidebar({
  open,
  onClose,
  view,
  setView,
  folders,
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onMoveSession,
  onOpenFolderModal,
  onDeleteSession,
  onDeleteFolder,
  onOpenTriad,
  mode,
  setMode,
  userProfile,
  onOpenSettings,
  onLogOut,
}) {
  const [collapsedFolders, setCollapsedFolders] = useState({})
  const [newChatMenuOpen, setNewChatMenuOpen] = useState(false)
  const [movingSessionId, setMovingSessionId] = useState(null)
  const [dragOverFolderId, setDragOverFolderId] = useState(null)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const newChatMenuRef = useRef(null)
  const moveMenuRef = useRef(null)
  const userMenuRef = useRef(null)

  // Auto-close popups when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (newChatMenuRef.current && !newChatMenuRef.current.contains(e.target)) {
        setNewChatMenuOpen(false)
      }
      if (moveMenuRef.current && !moveMenuRef.current.contains(e.target)) {
        setMovingSessionId(null)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('pointerdown', handleClickOutside)
    return () => document.removeEventListener('pointerdown', handleClickOutside)
  }, [])

  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0] || null
  const activeFolder =
    folders.find((f) => f.id === (activeSession?.folderId || 'f-general')) || folders[0]

  function toggleFolder(folderId) {
    setCollapsedFolders((prev) => ({
      ...prev,
      [folderId]: !prev[folderId],
    }))
  }

  function handleSelectSession(session) {
    onSelectSession(session.id)
    setView('chat')
    onClose()
  }

  function handleCreateInFolder(folderId) {
    onNewSession(folderId)
    setCollapsedFolders((prev) => ({ ...prev, [folderId]: false }))
    setView('chat')
    onClose()
  }

  return (
    <>
      {/* Mobile Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-ink/30 backdrop-blur-xs lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Content */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r border-neutral-200/80 bg-[#fbfbfa] px-3.5 pb-3.5 pt-3.5 transition-all duration-200 lg:static lg:h-[calc(100vh-60px)] ${
          open ? 'translate-x-0' : '-translate-x-full lg:hidden'
        }`}
      >
        {/* Header / Brand with Close Sidebar Button */}
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2 px-1 text-xs font-semibold text-neutral-700">
            <span className="grid h-6 w-6 place-items-center rounded-md bg-ocean/10 text-ocean text-[11px] font-bold">
              NE
            </span>
            <span>Clinical Workspace</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-200/70 hover:text-ink transition"
            title="Close sidebar"
            aria-label="Close sidebar"
          >
            <PanelLeftClose size={16} />
          </button>
        </div>

        {/* New Session Action with Folder Dropdown */}
        <div ref={newChatMenuRef} className="relative mb-4">
          <div className="flex w-full rounded-xl bg-ink text-white shadow-xs transition hover:bg-ocean">
            <button
              onClick={() => handleCreateInFolder(activeSession?.folderId || 'f-general')}
              className="flex flex-1 items-center justify-between px-3.5 py-2.5 text-xs font-semibold text-white truncate"
              title={`New chat session in ${activeFolder?.name || 'General Inquiries'}`}
            >
              <div className="flex items-center gap-2 truncate">
                <MessageSquarePlus size={16} className="shrink-0" />
                <span className="truncate">
                  {activeFolder && activeFolder.id !== 'f-general'
                    ? `New Chat (${activeFolder.name.split(' ')[0]})`
                    : 'New Chat Session'}
                </span>
              </div>
            </button>

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setNewChatMenuOpen((prev) => !prev)
              }}
              className="border-l border-white/20 px-2.5 hover:bg-white/10 rounded-r-xl transition flex items-center justify-center shrink-0"
              title="Select folder for new session"
              aria-label="Select folder for new session"
            >
              <ChevronDown
                size={14}
                className={`transition-transform duration-150 ${newChatMenuOpen ? 'rotate-180' : ''}`}
              />
            </button>
          </div>

          {newChatMenuOpen && (
            <div className="absolute left-0 top-full mt-1.5 z-50 w-full rounded-xl border border-neutral-200 bg-white p-1.5 shadow-xl text-xs">
              <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
                New Session In:
              </div>
              {folders.map((f) => {
                const isCurrent = (activeSession?.folderId || 'f-general') === f.id
                return (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => {
                      setNewChatMenuOpen(false)
                      handleCreateInFolder(f.id)
                    }}
                    className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition ${
                      isCurrent
                        ? 'bg-neutral-100 font-semibold text-ink'
                        : 'text-neutral-700 hover:bg-ocean/10 hover:text-ocean'
                    }`}
                  >
                    <Folder size={13} style={{ color: f.color }} className="shrink-0" />
                    <span className="truncate flex-1">{f.name}</span>
                    {isCurrent && (
                      <span className="text-[10px] text-ocean font-medium shrink-0">Current</span>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Scrollable Middle: Folders & Chat Sessions */}
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          {/* Workspaces & Folders Section */}
          <div>
            <div className="mb-2 flex items-center justify-between px-2">
              <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-400">
                Workspaces & Projects
              </span>
              <button
                onClick={onOpenFolderModal}
                className="flex items-center gap-1 text-[10px] font-semibold text-ocean hover:underline"
                title="Create a new folder / project"
              >
                <FolderPlus size={12} />
                <span>New</span>
              </button>
            </div>

            <div className="space-y-2">
              {folders.map((folder) => {
                const isCollapsed = Boolean(collapsedFolders[folder.id])
                const folderSessions = sessions.filter(
                  (s) => s.folderId === folder.id || (!s.folderId && folder.id === 'f-general')
                )
                const isDragOver = dragOverFolderId === folder.id

                return (
                  <div
                    key={folder.id}
                    onDragOver={(e) => {
                      e.preventDefault()
                      e.dataTransfer.dropEffect = 'move'
                      if (dragOverFolderId !== folder.id) {
                        setDragOverFolderId(folder.id)
                      }
                    }}
                    onDragLeave={(e) => {
                      if (e.currentTarget.contains(e.relatedTarget)) return
                      setDragOverFolderId(null)
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      const sessionId = e.dataTransfer.getData('text/plain')
                      if (sessionId && onMoveSession) {
                        onMoveSession(sessionId, folder.id)
                        setCollapsedFolders((prev) => ({ ...prev, [folder.id]: false }))
                      }
                      setDragOverFolderId(null)
                    }}
                    className={`rounded-xl border transition-all ${
                      isDragOver
                        ? 'border-ocean bg-ocean/10 ring-2 ring-ocean/30 shadow-xs'
                        : 'border-neutral-200/50 bg-white/60'
                    } p-1`}
                  >
                    {/* Folder Header */}
                    <div
                      onClick={() => toggleFolder(folder.id)}
                      className="group/folder flex cursor-pointer items-center justify-between rounded-lg px-2 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100 transition"
                    >
                      <div className="flex items-center gap-2 truncate min-w-0">
                        {isCollapsed ? (
                          <ChevronRight size={13} className="text-neutral-400 shrink-0" />
                        ) : (
                          <ChevronDown size={13} className="text-neutral-400 shrink-0" />
                        )}
                        <Folder
                          size={14}
                          className="shrink-0"
                          style={{ color: folder.color || '#0E6B70' }}
                        />
                        <span className="truncate">{folder.name}</span>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <span className="text-[10px] text-neutral-400 font-normal px-1">
                          {folderSessions.length}
                        </span>

                        {/* Direct "+ New Session" button for this folder */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleCreateInFolder(folder.id)
                          }}
                          className="rounded p-1 text-neutral-400 hover:bg-neutral-200/80 hover:text-ocean transition"
                          title={`New session in ${folder.name}`}
                          aria-label={`New session in ${folder.name}`}
                        >
                          <Plus size={13} />
                        </button>

                        {/* Delete button if custom folder */}
                        {!['f-general', 'f-pd', 'f-epi'].includes(folder.id) && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              if (
                                window.confirm(
                                  `Delete folder "${folder.name}"? Sessions will be moved to General Inquiries.`
                                )
                              ) {
                                onDeleteFolder?.(folder.id)
                              }
                            }}
                            className="rounded p-1 text-neutral-400 hover:bg-red-50 hover:text-red-500 transition"
                            title={`Delete ${folder.name}`}
                          >
                            <Trash2 size={11} />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Folder Chat Sessions */}
                    {!isCollapsed && (
                      <div className="mt-1 space-y-0.5 pl-3">
                        {folderSessions.length === 0 ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleCreateInFolder(folder.id)
                            }}
                            className="group/btn flex w-full items-center gap-2 rounded-lg border border-dashed border-neutral-300/80 bg-neutral-50/50 px-2.5 py-1.5 text-left text-[11px] text-neutral-500 hover:border-ocean hover:bg-ocean/5 hover:text-ocean transition"
                            title={`Create new session in ${folder.name}`}
                          >
                            <Plus
                              size={12}
                              className="shrink-0 text-neutral-400 group-hover/btn:text-ocean transition"
                            />
                            <span className="truncate">New session here</span>
                          </button>
                        ) : (
                          folderSessions.map((session) => {
                            const isActive = view === 'chat' && activeSessionId === session.id
                            return (
                              <div
                                key={session.id}
                                draggable
                                onDragStart={(e) => {
                                  e.dataTransfer.setData('text/plain', session.id)
                                  e.dataTransfer.effectAllowed = 'move'
                                }}
                                onClick={() => handleSelectSession(session)}
                                className={`group relative flex cursor-pointer items-center justify-between rounded-lg px-2 py-1.5 text-xs transition ${
                                  isActive
                                    ? 'bg-neutral-200/80 font-semibold text-ink'
                                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-ink'
                                }`}
                              >
                                <div className="flex items-start gap-2 min-w-0 flex-1">
                                  <MessageSquare
                                    size={13}
                                    className={`mt-0.5 shrink-0 ${
                                      isActive ? 'text-ocean' : 'text-neutral-400'
                                    }`}
                                  />
                                  <div className="min-w-0 flex-1">
                                    <p className="truncate text-xs leading-snug">
                                      {session.title || 'Untitled Session'}
                                    </p>
                                    <p className="text-[10px] text-neutral-400 font-normal leading-tight mt-0.5">
                                      {formatSessionTimestamp(session.timestamp)}
                                    </p>
                                  </div>
                                </div>

                                <div className="ml-1 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5">
                                  {/* Move to folder action */}
                                  <div className="relative">
                                    <button
                                      type="button"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        setMovingSessionId((prev) =>
                                          prev === session.id ? null : session.id
                                        )
                                      }}
                                      className="rounded p-1 text-neutral-400 hover:bg-neutral-200/80 hover:text-ocean transition"
                                      title="Move session to folder..."
                                    >
                                      <FolderInput size={12} />
                                    </button>

                                    {movingSessionId === session.id && (
                                      <div
                                        ref={moveMenuRef}
                                        onClick={(e) => e.stopPropagation()}
                                        className="absolute right-0 top-full mt-1 z-50 w-48 rounded-xl border border-neutral-200 bg-white p-1.5 shadow-xl text-xs"
                                      >
                                        <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
                                          Move to Folder:
                                        </div>
                                        {folders.map((f) => {
                                          const isCurrent =
                                            (session.folderId || 'f-general') === f.id
                                          return (
                                            <button
                                              key={f.id}
                                              type="button"
                                              disabled={isCurrent}
                                              onClick={() => {
                                                onMoveSession?.(session.id, f.id)
                                                setMovingSessionId(null)
                                              }}
                                              className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs transition ${
                                                isCurrent
                                                  ? 'opacity-40 cursor-default bg-neutral-50 font-medium'
                                                  : 'text-neutral-700 hover:bg-ocean/10 hover:text-ocean'
                                              }`}
                                            >
                                              <Folder
                                                size={12}
                                                style={{ color: f.color }}
                                                className="shrink-0"
                                              />
                                              <span className="truncate flex-1">{f.name}</span>
                                              {isCurrent && (
                                                <Check
                                                  size={11}
                                                  className="text-neutral-400 shrink-0"
                                                />
                                              )}
                                            </button>
                                          )
                                        })}
                                      </div>
                                    )}
                                  </div>

                                  {/* Delete session */}
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      onDeleteSession(session.id)
                                    }}
                                    className="rounded p-1 text-neutral-400 hover:bg-neutral-200/80 hover:text-red-600 transition"
                                    title="Delete session"
                                  >
                                    <Trash2 size={12} />
                                  </button>
                                </div>
                              </div>
                            )
                          })
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Research & Benchmarks */}
          <div>
            <div className="mb-1 px-2 text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-400">
              Evaluation & Benchmarks
            </div>
            <div className="space-y-0.5">
              <button
                onClick={() => {
                  setView('evaluation')
                  onClose()
                }}
                className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-xs font-medium transition ${
                  view === 'evaluation'
                    ? 'bg-neutral-200/70 font-semibold text-ink'
                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-ink'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <BarChart3
                    size={15}
                    className={view === 'evaluation' ? 'text-ocean' : 'text-neutral-400'}
                  />
                  <span>Evaluation & Metrics</span>
                </div>
                <ChevronRight size={13} className="text-neutral-400" />
              </button>
            </div>
          </div>

          {/* Execution Mode Selector */}
          <div>
            <div className="mb-1.5 px-2 text-[10px] font-bold uppercase tracking-[0.16em] text-neutral-400">
              Execution Mode
            </div>
            <div className="rounded-xl border border-neutral-200/80 bg-white p-1 shadow-2xs space-y-1">
              <button
                onClick={() => setMode('rag_verified')}
                className={`flex w-full items-start gap-2 rounded-lg p-2 text-left transition ${
                  mode === 'rag_verified'
                    ? 'bg-mint/60 text-ocean'
                    : 'text-neutral-600 hover:bg-neutral-50'
                }`}
              >
                <ShieldCheck size={15} className="mt-0.5 shrink-0 text-ocean" />
                <div>
                  <div className="text-xs font-bold leading-none">Verified RAG (Proposed)</div>
                  <div className="text-[10px] opacity-75 mt-0.5">Triad retrieval & NLI checks</div>
                </div>
              </button>
              <button
                onClick={() => setMode('baseline')}
                className={`flex w-full items-start gap-2 rounded-lg p-2 text-left transition ${
                  mode === 'baseline'
                    ? 'bg-neutral-100 text-ink font-semibold'
                    : 'text-neutral-500 hover:bg-neutral-50'
                }`}
              >
                <Cloud size={15} className={`mt-0.5 shrink-0 ${mode === 'baseline' ? 'text-amber-600' : 'text-neutral-400'}`} />
                <div>
                  <div className="text-xs font-semibold leading-none">Cloud Baseline (Gemini)</div>
                  <div className="text-[10px] opacity-75 mt-0.5">Parametric zero-shot (No RAG)</div>
                </div>
              </button>
              <button
                onClick={() => setMode('ollama_baseline')}
                className={`flex w-full items-start gap-2 rounded-lg p-2 text-left transition ${
                  mode === 'ollama_baseline'
                    ? 'bg-neutral-100 text-ink font-semibold'
                    : 'text-neutral-500 hover:bg-neutral-50'
                }`}
              >
                <Cpu size={15} className={`mt-0.5 shrink-0 ${mode === 'ollama_baseline' ? 'text-purple-600' : 'text-neutral-400'}`} />
                <div>
                  <div className="text-xs font-semibold leading-none">Local Baseline (Ollama)</div>
                  <div className="text-[10px] opacity-75 mt-0.5">On-device zero-shot (Offline)</div>
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Bottom Left Footer: Research Pill & User Profile / Settings / Log Out */}
        <div className="mt-auto pt-2.5 border-t border-neutral-200/70 space-y-2">
          {/* Subtle Research Disclaimer Pill */}
          <div className="flex items-center justify-between px-1.5 text-[10px] text-neutral-400">
            <div className="flex items-center gap-1.5">
              <HeartPulse size={12} className="text-coral shrink-0" />
              <span className="font-semibold text-neutral-600">Research MVP</span>
            </div>
            <span className="text-[9px] text-neutral-400">Educational Use</span>
          </div>

          {/* User Profile Card & Action Bar */}
          <div className="relative">
            <div className="flex items-center justify-between rounded-xl border border-neutral-200/80 bg-white p-1.5 shadow-2xs">
              {/* User Identity Button */}
              <button
                type="button"
                onClick={() => setUserMenuOpen((prev) => !prev)}
                className="flex items-center gap-2 min-w-0 flex-1 text-left rounded-lg p-1 hover:bg-neutral-50 transition"
                title={`${userProfile?.name || 'Dr. Daniel'} (${userProfile?.role || 'Clinical Neurologist'})`}
              >
                <div className="relative shrink-0">
                  <div className="grid h-7 w-7 place-items-center rounded-lg bg-ocean font-bold text-white text-[11px] shadow-2xs">
                    {userProfile?.name
                      ? userProfile.name
                          .split(' ')
                          .map((n) => n[0])
                          .join('')
                          .slice(0, 2)
                          .toUpperCase()
                      : 'DP'}
                  </div>
                  <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border border-white bg-emerald-500" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold text-ink truncate leading-tight">
                    {userProfile?.name || 'Dr. Daniel'}
                  </div>
                  <div className="text-[10px] text-neutral-400 truncate leading-tight mt-0.5">
                    {userProfile?.role || 'Clinical Neurologist'}
                  </div>
                </div>
              </button>

              {/* Action Buttons: Settings & Log Out */}
              <div className="flex items-center gap-0.5 shrink-0 ml-1">
                <button
                  type="button"
                  onClick={onOpenSettings}
                  className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-ink transition"
                  title="Settings"
                  aria-label="Settings"
                >
                  <Settings size={15} />
                </button>
                <button
                  type="button"
                  onClick={onLogOut}
                  className="rounded-lg p-1.5 text-neutral-400 hover:bg-red-50 hover:text-red-500 transition"
                  title="Log out"
                  aria-label="Log out"
                >
                  <LogOut size={15} />
                </button>
              </div>
            </div>

            {/* User Popover Menu */}
            {userMenuOpen && (
              <div
                ref={userMenuRef}
                className="absolute bottom-full left-0 mb-1.5 z-50 w-full rounded-xl border border-neutral-200 bg-white p-1.5 shadow-xl text-xs"
              >
                <div className="px-2.5 py-2 border-b border-neutral-100">
                  <div className="font-semibold text-ink text-xs">{userProfile?.name || 'Dr. Daniel'}</div>
                  <div className="text-[10px] text-neutral-400">{userProfile?.email || 'daniel.puah@clinical.org'}</div>
                  <div className="text-[10px] text-emerald-600 font-medium mt-1 flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    <span>Clinician Workspace Active</span>
                  </div>
                </div>
                <div className="py-1">
                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false)
                      onOpenSettings()
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-neutral-700 hover:bg-neutral-100 transition"
                  >
                    <Settings size={14} className="text-neutral-500" />
                    <span>Workspace Settings</span>
                  </button>
                </div>
                <div className="pt-1 border-t border-neutral-100">
                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false)
                      onLogOut()
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-red-600 hover:bg-red-50 transition"
                  >
                    <LogOut size={14} />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  )
}
