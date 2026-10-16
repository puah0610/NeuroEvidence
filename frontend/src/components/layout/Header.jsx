import { useEffect, useRef, useState } from 'react'
import {
  Brain,
  Check,
  ChevronDown,
  Edit2,
  Folder,
  Layers,
  PanelLeftClose,
  PanelLeftOpen,
  RotateCcw,
} from 'lucide-react'
import { formatSessionTimestamp } from '../../utils/sessionStore'

export default function Header({
  health,
  onMenu,
  onOpenTriad,
  activeSession,
  onUpdateSessionTitle,
  onClearSession,
  folders,
  onMoveSession,
  sidebarOpen,
  onToggleSidebar,
}) {
  const [editing, setEditing] = useState(false)
  const [tempTitle, setTempTitle] = useState('')
  const [folderDropdownOpen, setFolderDropdownOpen] = useState(false)
  const folderDropdownRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (folderDropdownRef.current && !folderDropdownRef.current.contains(e.target)) {
        setFolderDropdownOpen(false)
      }
    }
    document.addEventListener('pointerdown', handleClickOutside)
    return () => document.removeEventListener('pointerdown', handleClickOutside)
  }, [])

  const currentFolder =
    folders?.find((f) => f.id === (activeSession?.folderId || 'f-general')) ||
    folders?.[0] ||
    null

  function startEdit() {
    setTempTitle(activeSession?.title || 'New Query Session')
    setEditing(true)
  }

  function saveEdit() {
    if (tempTitle.trim() && activeSession) {
      onUpdateSessionTitle(activeSession.id, tempTitle.trim())
    }
    setEditing(false)
  }

  return (
    <header className="sticky top-0 z-30 h-[60px] border-b border-neutral-200/80 bg-white/95 px-4 backdrop-blur-md sm:px-6">
      <div className="flex h-full items-center justify-between">
        {/* Left: Sidebar toggle, Logo & Active Session Name */}
        <div className="flex items-center gap-2.5 min-w-0">
          <button
            type="button"
            onClick={onToggleSidebar || onMenu}
            className={`rounded-lg p-1.5 text-neutral-500 hover:bg-neutral-100 hover:text-ink transition shrink-0 ${
              sidebarOpen ? 'lg:hidden' : 'inline-flex'
            }`}
            title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          >
            {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>

          {!sidebarOpen && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs font-semibold text-neutral-700 bg-neutral-100 px-2.5 py-1 rounded-lg border border-neutral-200/80 shrink-0">
              <span className="grid h-4 w-4 place-items-center rounded bg-ocean/15 text-ocean text-[9px] font-bold">
                NE
              </span>
              <span>Clinical Workspace</span>
            </div>
          )}

          <div className="flex items-center gap-2 shrink-0">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-ink text-white shadow-xs">
              <Brain size={18} strokeWidth={2} />
            </div>
            <div className="hidden sm:block">
              <span className="font-display text-base font-bold tracking-tight text-ink">
                NeuroEvidence
              </span>
            </div>
          </div>

          <span className="hidden text-neutral-300 md:inline shrink-0">/</span>

          {/* Active Session Title & Timestamp */}
          <div className="min-w-0 flex items-center gap-2">
            {editing ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="text"
                  autoFocus
                  value={tempTitle}
                  onChange={(e) => setTempTitle(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
                  className="rounded-lg border border-ocean px-2 py-0.5 text-xs font-semibold text-ink outline-none"
                />
                <button
                  onClick={saveEdit}
                  className="rounded-md bg-ocean p-1 text-white hover:bg-ink transition"
                >
                  <Check size={12} />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 min-w-0">
                <span className="truncate text-xs font-semibold text-neutral-700">
                  {activeSession?.title || 'New Query Session'}
                </span>
                <button
                  onClick={startEdit}
                  className="text-neutral-400 hover:text-ink transition shrink-0"
                  title="Rename session"
                >
                  <Edit2 size={12} />
                </button>
                {activeSession?.timestamp && (
                  <span className="hidden lg:inline text-[10px] text-neutral-400 font-normal shrink-0">
                    • {formatSessionTimestamp(activeSession.timestamp)}
                  </span>
                )}
              </div>
            )}

            {/* Folder badge with dropdown to move current session */}
            {activeSession && folders && folders.length > 0 && (
              <div ref={folderDropdownRef} className="relative shrink-0 ml-1">
                <button
                  type="button"
                  onClick={() => setFolderDropdownOpen((prev) => !prev)}
                  className="flex items-center gap-1.5 rounded-lg border border-neutral-200/90 bg-neutral-50 px-2 py-1 text-[11px] font-medium text-neutral-600 hover:border-neutral-300 hover:bg-neutral-100 hover:text-ink transition"
                  title="Current folder (click to move this session)"
                >
                  <Folder
                    size={12}
                    style={{ color: currentFolder?.color || '#0E6B70' }}
                    className="shrink-0"
                  />
                  <span className="max-w-[130px] truncate hidden md:inline">
                    {currentFolder?.name || 'General Inquiries'}
                  </span>
                  <ChevronDown
                    size={11}
                    className={`text-neutral-400 transition-transform duration-150 ${
                      folderDropdownOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>

                {folderDropdownOpen && (
                  <div className="absolute left-0 top-full mt-1.5 z-50 w-52 rounded-xl border border-neutral-200 bg-white p-1.5 shadow-xl text-xs">
                    <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
                      Move Session To:
                    </div>
                    {folders.map((f) => {
                      const isSelected = (activeSession.folderId || 'f-general') === f.id
                      return (
                        <button
                          key={f.id}
                          type="button"
                          onClick={() => {
                            onMoveSession?.(activeSession.id, f.id)
                            setFolderDropdownOpen(false)
                          }}
                          className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs transition ${
                            isSelected
                              ? 'bg-neutral-100 font-semibold text-ink'
                              : 'text-neutral-600 hover:bg-ocean/10 hover:text-ocean'
                          }`}
                        >
                          <Folder size={12} style={{ color: f.color }} className="shrink-0" />
                          <span className="truncate flex-1">{f.name}</span>
                          {isSelected && <Check size={12} className="text-ocean shrink-0" />}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Triad KB overview modal trigger */}
          <button
            onClick={onOpenTriad}
            className="hidden items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-neutral-700 shadow-2xs transition hover:border-neutral-300 hover:bg-neutral-50 sm:inline-flex"
          >
            <Layers size={14} className="text-ocean" />
            <span>3-Layer Triad KB</span>
          </button>

          {/* Health indicator */}
          <div className="flex items-center gap-1.5 rounded-lg border border-neutral-200/80 bg-neutral-50/80 px-2.5 py-1.5 text-[11px] font-medium text-neutral-600">
            <span
              className={`h-2 w-2 rounded-full ${
                health?.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
            <span className="hidden sm:inline">
              {health?.demo_mode ? 'Demo Corpus' : 'Research Corpus'}
            </span>
          </div>

          {/* Clear Session */}
          <button
            onClick={onClearSession}
            className="flex items-center gap-1 rounded-lg border border-neutral-200 p-1.5 text-neutral-500 hover:bg-neutral-100 hover:text-ink transition"
            title="Clear current session chat"
          >
            <RotateCcw size={15} />
          </button>
        </div>
      </div>
    </header>
  )
}
