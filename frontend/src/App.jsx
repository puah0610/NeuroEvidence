import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import Header from './components/layout/Header'
import Sidebar from './components/layout/Sidebar'
import ChatPane from './components/chat/ChatPane'
import EvaluationView from './components/eval/EvaluationView'
import TriadModal from './components/common/TriadModal'
import FolderModal from './components/common/FolderModal'
import SettingsModal from './components/common/SettingsModal'
import AuthModal from './components/common/AuthModal'
import {
  createNewSession,
  getStoredFolders,
  getStoredSessions,
  getStoredSettings,
  getStoredUser,
  saveStoredFolders,
  saveStoredSessions,
  saveStoredUser,
} from './utils/sessionStore'

export default function App() {
  const [view, setView] = useState('chat') // 'chat' | 'evaluation'
  const [folders, setFolders] = useState(getStoredFolders)
  const [sessions, setSessions] = useState(() => {
    const stored = getStoredSessions()
    if (stored && stored.length > 0) return stored
    const initial = createNewSession('f-general', 'New Query Session')
    return [initial]
  })

  const [activeSessionId, setActiveSessionId] = useState(() => {
    const stored = getStoredSessions()
    return stored && stored.length > 0 ? stored[0].id : null
  })

  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState('rag_verified')
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState(null)
  const [summary, setSummary] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [triadModalOpen, setTriadModalOpen] = useState(false)
  const [folderModalOpen, setFolderModalOpen] = useState(false)
  const [userProfile, setUserProfile] = useState(getStoredUser)
  const [settingsModalOpen, setSettingsModalOpen] = useState(false)
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const endRef = useRef(null)

  // Ensure activeSessionId is valid
  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id)
    }
  }, [sessions, activeSessionId])

  // Sync sessions to localStorage
  useEffect(() => {
    saveStoredSessions(sessions)
  }, [sessions])

  // Sync folders to localStorage
  useEffect(() => {
    saveStoredFolders(folders)
  }, [folders])

  // Initial health check
  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth({ status: 'degraded', demo_mode: true }))
  }, [])

  // Auto-scroll when active session messages change
  const activeSession = useMemo(() => {
    return sessions.find((s) => s.id === activeSessionId) || sessions[0] || null
  }, [sessions, activeSessionId])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [activeSession?.messages, loading])

  // Evaluation summary
  useEffect(() => {
    if (view === 'evaluation') {
      api.summary().then(setSummary).catch(() => setSummary(null))
    }
  }, [view])

  // Create new session
  function handleNewSession(folderId = 'f-general') {
    const fresh = createNewSession(folderId, 'New Query Session')
    setSessions((prev) => [fresh, ...prev])
    setActiveSessionId(fresh.id)
    setQuestion('')
  }

  // Delete session
  function handleDeleteSession(sessionId) {
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== sessionId)
      if (sessionId === activeSessionId) {
        if (remaining.length > 0) {
          setActiveSessionId(remaining[0].id)
        } else {
          const fresh = createNewSession('f-general', 'New Query Session')
          setActiveSessionId(fresh.id)
          return [fresh]
        }
      }
      return remaining
    })
  }

  // Update session title
  function handleUpdateSessionTitle(sessionId, newTitle) {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle } : s))
    )
  }

  // Clear current session messages
  function handleClearCurrentSession() {
    if (!activeSessionId) return
    setSessions((prev) =>
      prev.map((s) => (s.id === activeSessionId ? { ...s, messages: [] } : s))
    )
  }

  // Create new user project / folder
  function handleCreateFolder(newFolder) {
    setFolders((prev) => [...prev, newFolder])
  }

  // Move session to another folder
  function handleMoveSession(sessionId, targetFolderId) {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === sessionId
          ? { ...s, folderId: targetFolderId, lastUpdated: Date.now() }
          : s
      )
    )
  }

  // Delete custom folder
  function handleDeleteFolder(folderId) {
    if (['f-general', 'f-pd', 'f-epi'].includes(folderId)) return
    setSessions((prev) =>
      prev.map((s) => (s.folderId === folderId ? { ...s, folderId: 'f-general' } : s))
    )
    setFolders((prev) => prev.filter((f) => f.id !== folderId))
  }

  // Update clinician profile
  function handleSaveProfile(newProfile) {
    setUserProfile(newProfile)
    saveStoredUser(newProfile)
  }

  // Clear all sessions
  function handleClearAllSessions() {
    const fresh = createNewSession('f-general', 'New Query Session')
    setSessions([fresh])
    setActiveSessionId(fresh.id)
  }

  // Auth / session handlers
  function handleLogOut() {
    setAuthModalOpen(true)
  }

  function handleLogin() {
    setAuthModalOpen(false)
  }

  // Submit query in the active session
  async function submit(value = question) {
    const clean = value.trim()
    if (!clean || loading || !activeSession) return
    setQuestion('')

    // Append user message & update title if it's the first message
    const updatedMessagesWithUser = [
      ...(activeSession.messages || []),
      { role: 'user', text: clean },
    ]

    const newTitle =
      activeSession.messages.length === 0 &&
      (activeSession.title === 'New Query Session' || !activeSession.title)
        ? clean.length > 40
          ? `${clean.slice(0, 40)}…`
          : clean
        : activeSession.title

    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              title: newTitle,
              messages: updatedMessagesWithUser,
              lastUpdated: Date.now(),
            }
          : s
      )
    )

    setLoading(true)

    try {
      const storedSettings = getStoredSettings()
      const enableLivePubMed = storedSettings?.general?.enableLivePubMed ?? true

      const history = (activeSession.messages || [])
        .map((m) => ({
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.role === 'assistant' ? (m.result?.answer || m.text || '') : (m.text || ''),
        }))
        .filter((h) => h.content)

      const result = await api.chat({
        session_id: activeSession.id,
        question: clean,
        mode,
        enable_live_pubmed: enableLivePubMed,
        history: history.slice(-6),
      })

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSession.id
            ? {
                ...s,
                messages: [...updatedMessagesWithUser, { role: 'assistant', result }],
                lastUpdated: Date.now(),
              }
            : s
        )
      )
    } catch (error) {
      const detail =
        error.response?.data?.detail || 'The assistant could not reach the research API.'
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSession.id
            ? {
                ...s,
                messages: [...updatedMessagesWithUser, { role: 'error', text: detail }],
                lastUpdated: Date.now(),
              }
            : s
        )
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-white text-ink antialiased">
      {/* Top Application Header */}
      <Header
        health={health}
        onMenu={() => setSidebarOpen(true)}
        onOpenTriad={() => setTriadModalOpen(true)}
        activeSession={activeSession}
        onUpdateSessionTitle={handleUpdateSessionTitle}
        onClearSession={handleClearCurrentSession}
        folders={folders}
        onMoveSession={handleMoveSession}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
      />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Navigation Sidebar with Workspaces & Sessions */}
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          view={view}
          setView={setView}
          folders={folders}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
          onNewSession={handleNewSession}
          onMoveSession={handleMoveSession}
          onOpenFolderModal={() => setFolderModalOpen(true)}
          onDeleteSession={handleDeleteSession}
          onDeleteFolder={handleDeleteFolder}
          onOpenTriad={() => setTriadModalOpen(true)}
          mode={mode}
          setMode={setMode}
          userProfile={userProfile}
          onOpenSettings={() => setSettingsModalOpen(true)}
          onLogOut={handleLogOut}
        />

        {/* Main Body: Center Copilot Chat Area takes the stage */}
        <main className="flex flex-1 min-h-0 min-w-0 overflow-hidden">
          {view === 'evaluation' ? (
            <div className="flex-1 overflow-y-auto">
              <EvaluationView summary={summary} />
            </div>
          ) : (
            <div className="flex-1 min-w-0 h-full">
              <ChatPane
                messages={activeSession?.messages || []}
                question={question}
                setQuestion={setQuestion}
                submit={submit}
                loading={loading}
                mode={mode}
                endRef={endRef}
                onOpenTriad={() => setTriadModalOpen(true)}
              />
            </div>
          )}
        </main>
      </div>

      {/* 3-Layer Triad Architecture Modal */}
      {triadModalOpen && <TriadModal onClose={() => setTriadModalOpen(false)} />}

      {/* New Project / Folder Modal */}
      <FolderModal
        isOpen={folderModalOpen}
        onClose={() => setFolderModalOpen(false)}
        onCreateFolder={handleCreateFolder}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={settingsModalOpen}
        onClose={() => setSettingsModalOpen(false)}
        userProfile={userProfile}
        onSaveProfile={handleSaveProfile}
        sessionsCount={sessions.length}
        onClearAllSessions={handleClearAllSessions}
      />

      {/* Authentication / Sign In Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onLogin={handleLogin}
        userProfile={userProfile}
      />
    </div>
  )
}
