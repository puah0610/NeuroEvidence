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
  DEFAULT_FOLDERS,
  getStoredAuth,
  getStoredFolders,
  getStoredSessions,
  getStoredSettings,
  getStoredUser,
  saveStoredAuth,
  saveStoredFolders,
  saveStoredSessions,
  saveStoredSettings,
  saveStoredUser,
} from './utils/sessionStore'

function loadInitialUserWorkspace(userId) {
  if (!userId) {
    return {
      folders: DEFAULT_FOLDERS.map((f) => ({ ...f })),
      sessions: [],
      activeSessionId: null,
    }
  }
  const folders = getStoredFolders(userId)
  const stored = getStoredSessions(userId)
  const sessions =
    stored && stored.length > 0
      ? stored
      : [createNewSession('f-general', 'New Query Session')]
  return {
    folders,
    sessions,
    activeSessionId: sessions[0]?.id || null,
  }
}

export default function App() {
  const [authSession, setAuthSession] = useState(getStoredAuth)
  const currentUserId = authSession?.isAuthenticated
    ? authSession.userId || (authSession.accountRole === 'admin' ? 'admin' : 'puah')
    : null

  const initialWorkspace = useMemo(() => loadInitialUserWorkspace(currentUserId), [])

  const [view, setView] = useState('chat') // 'chat' | 'evaluation'
  const [folders, setFolders] = useState(initialWorkspace.folders)
  const [sessions, setSessions] = useState(initialWorkspace.sessions)
  const [activeSessionId, setActiveSessionId] = useState(initialWorkspace.activeSessionId)

  const [question, setQuestion] = useState('')
  const [researchMode, setResearchMode] = useState(() => {
    return localStorage.getItem('neuroevidence_research_mode') === 'true'
  })
  const [mode, setMode] = useState('rag_verified')
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState(null)
  const [summary, setSummary] = useState(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [triadModalOpen, setTriadModalOpen] = useState(false)
  const [folderModalOpen, setFolderModalOpen] = useState(false)
  const [userProfile, setUserProfile] = useState(() => getStoredUser(currentUserId || 'admin'))
  const [workspaceSettings, setWorkspaceSettings] = useState(() =>
    getStoredSettings(currentUserId || 'admin')
  )
  const [settingsModalOpen, setSettingsModalOpen] = useState(false)
  const workspaceOwnerRef = useRef(currentUserId)
  const endRef = useRef(null)

  const isAdmin = Boolean(authSession?.isAuthenticated && authSession?.accountRole === 'admin')
  const effectiveResearchMode = isAdmin && researchMode
  const effectiveMode = effectiveResearchMode ? mode : 'rag_verified'
  const effectiveView = isAdmin && view === 'evaluation' ? 'evaluation' : 'chat'
  const activeTheme = workspaceSettings?.general?.theme === 'dark' ? 'dark' : 'light'

  // Sync auth state to localStorage
  useEffect(() => {
    saveStoredAuth(authSession)
  }, [authSession])

  // Load isolated per-user workspace from localStorage + backend folder (data/users/<user_id>/)
  useEffect(() => {
    let cancelled = false

    if (!currentUserId) {
      workspaceOwnerRef.current = null
      setFolders(DEFAULT_FOLDERS.map((f) => ({ ...f })))
      setSessions([])
      setActiveSessionId(null)
      return
    }

    // 1. Immediately switch UI state to this user's isolated local cache
    const localData = loadInitialUserWorkspace(currentUserId)
    workspaceOwnerRef.current = currentUserId
    setFolders(localData.folders)
    setSessions(localData.sessions)
    setActiveSessionId(localData.activeSessionId)
    setUserProfile(getStoredUser(currentUserId))
    setWorkspaceSettings(getStoredSettings(currentUserId))

    // 2. Sync with backend per-user folder (creates data/users/<user_id>/ automatically if new user)
    api
      .getUserWorkspace(currentUserId)
      .then(async (remote) => {
        if (cancelled || workspaceOwnerRef.current !== currentUserId) return

        const remoteFolders =
          Array.isArray(remote?.folders) && remote.folders.length > 0
            ? remote.folders
            : localData.folders
        const remoteSessions = Array.isArray(remote?.sessions) ? remote.sessions : []

        if (remoteSessions.length > 0) {
          setFolders(remoteFolders)
          setSessions(remoteSessions)
          setActiveSessionId(remoteSessions[0].id)
          saveStoredFolders(remoteFolders, currentUserId)
          saveStoredSessions(remoteSessions, currentUserId)
        } else {
          // Brand-new server folder for this user: seed it with any local sessions/folders
          const hasLocalContent = localData.sessions.some(
            (s) => (s.messages && s.messages.length > 0) || s.title !== 'New Query Session'
          )
          await api.saveUserFolders(currentUserId, localData.folders).catch(() => {})
          if (hasLocalContent) {
            for (const sess of localData.sessions) {
              await api.saveUserSession(currentUserId, sess).catch(() => {})
            }
          } else if (localData.sessions[0]) {
            await api.saveUserSession(currentUserId, localData.sessions[0]).catch(() => {})
          }
        }
      })
      .catch(() => {
        // Offline / API unavailable: isolated localStorage state remains active
      })

    return () => {
      cancelled = true
    }
  }, [currentUserId])

  // Apply light/dark class on <html>
  useEffect(() => {
    const root = document.documentElement
    if (activeTheme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [activeTheme])

  function handleToggleTheme() {
    const nextTheme = activeTheme === 'dark' ? 'light' : 'dark'
    const nextSettings = {
      ...workspaceSettings,
      general: {
        ...workspaceSettings?.general,
        theme: nextTheme,
      },
    }
    handleSaveSettings(nextSettings)
  }

  function handleToggleResearchMode() {
    if (!isAdmin) return
    setResearchMode((prev) => {
      const next = !prev
      localStorage.setItem('neuroevidence_research_mode', String(next))
      if (!next) {
        setMode('rag_verified')
        setView('chat')
      }
      return next
    })
  }

  function handleOpenEvaluation() {
    if (!isAdmin) return
    if (!researchMode) {
      setResearchMode(true)
      localStorage.setItem('neuroevidence_research_mode', 'true')
    }
    setView('evaluation')
  }

  function handleSignIn({ userId, accountRole, profile }) {
    const resolvedUserId = userId || (accountRole === 'admin' ? 'admin' : 'puah')
    const nextAuth = { isAuthenticated: true, userId: resolvedUserId, accountRole }

    if (profile) {
      saveStoredUser(profile, resolvedUserId)
      const existingSettings = getStoredSettings(resolvedUserId)
      saveStoredSettings({ ...existingSettings, profile }, resolvedUserId)
    }

    if (accountRole !== 'admin') {
      setResearchMode(false)
      localStorage.setItem('neuroevidence_research_mode', 'false')
      setMode('rag_verified')
      setView('chat')
    }

    setAuthSession(nextAuth)
    saveStoredAuth(nextAuth)
  }

  function handleSignOut() {
    const nextAuth = { isAuthenticated: false, userId: null, accountRole: null }
    workspaceOwnerRef.current = null
    setAuthSession(nextAuth)
    saveStoredAuth(nextAuth)
    setView('chat')
    setMode('rag_verified')
    setQuestion('')
    setSettingsModalOpen(false)
    setTriadModalOpen(false)
    setFolderModalOpen(false)
  }

  async function refreshSummary() {
    setSummaryLoading(true)
    try {
      const data = await api.summary()
      setSummary(data)
    } catch {
      setSummary(null)
    } finally {
      setSummaryLoading(false)
    }
  }

  // Ensure activeSessionId is valid
  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id)
    }
  }, [sessions, activeSessionId])

  // Sync sessions to current user's isolated localStorage key
  useEffect(() => {
    if (currentUserId && workspaceOwnerRef.current === currentUserId) {
      saveStoredSessions(sessions, currentUserId)
    }
  }, [sessions, currentUserId])

  // Sync folders to current user's isolated localStorage key
  useEffect(() => {
    if (currentUserId && workspaceOwnerRef.current === currentUserId) {
      saveStoredFolders(folders, currentUserId)
    }
  }, [folders, currentUserId])

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
    if (workspaceSettings?.general?.autoScroll !== false) {
      endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [activeSession?.messages, loading, workspaceSettings?.general?.autoScroll])

  // Evaluation summary
  useEffect(() => {
    if (effectiveView === 'evaluation') {
      refreshSummary()
    }
  }, [effectiveView])

  // Create new session (isolated to current user's folder)
  function handleNewSession(folderId = 'f-general') {
    const fresh = createNewSession(folderId, 'New Query Session')
    setSessions((prev) => [fresh, ...prev])
    setActiveSessionId(fresh.id)
    setQuestion('')
    if (currentUserId) {
      api.saveUserSession(currentUserId, fresh).catch(() => {})
    }
  }

  // Delete session (isolated to current user's folder)
  function handleDeleteSession(sessionId) {
    if (currentUserId) {
      api.deleteUserSession(currentUserId, sessionId).catch(() => {})
    }
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== sessionId)
      if (sessionId === activeSessionId) {
        if (remaining.length > 0) {
          setActiveSessionId(remaining[0].id)
        } else {
          const fresh = createNewSession('f-general', 'New Query Session')
          setActiveSessionId(fresh.id)
          if (currentUserId) {
            api.saveUserSession(currentUserId, fresh).catch(() => {})
          }
          return [fresh]
        }
      }
      return remaining
    })
  }

  // Update session title
  function handleUpdateSessionTitle(sessionId, newTitle) {
    const cleanTitle = (newTitle || '').trim()
    if (!cleanTitle) return
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === sessionId) {
          const updated = {
            ...s,
            title: cleanTitle,
            customTitle: true,
            lastUpdated: Date.now(),
          }
          if (currentUserId) {
            api.saveUserSession(currentUserId, updated).catch(() => {})
          }
          return updated
        }
        return s
      })
    )
  }

  // Clear current session messages
  function handleClearCurrentSession() {
    if (!activeSessionId) return
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSessionId) {
          const updated = { ...s, messages: [], lastUpdated: Date.now() }
          if (currentUserId) {
            api.saveUserSession(currentUserId, updated).catch(() => {})
          }
          return updated
        }
        return s
      })
    )
  }

  // Create new user project / folder
  function handleCreateFolder(newFolder) {
    setFolders((prev) => {
      const next = [...prev, newFolder]
      if (currentUserId) {
        api.saveUserFolders(currentUserId, next).catch(() => {})
      }
      return next
    })
  }

  // Move session to another folder
  function handleMoveSession(sessionId, targetFolderId) {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === sessionId) {
          const updated = { ...s, folderId: targetFolderId, lastUpdated: Date.now() }
          if (currentUserId) {
            api.saveUserSession(currentUserId, updated).catch(() => {})
          }
          return updated
        }
        return s
      })
    )
  }

  // Delete custom folder
  function handleDeleteFolder(folderId) {
    if (['f-general', 'f-pd', 'f-epi'].includes(folderId)) return
    const movedSessions = []
    setSessions((prev) =>
      prev.map((s) => {
        if (s.folderId === folderId) {
          const updated = { ...s, folderId: 'f-general', lastUpdated: Date.now() }
          movedSessions.push(updated)
          return updated
        }
        return s
      })
    )
    setFolders((prev) => {
      const next = prev.filter((f) => f.id !== folderId)
      if (currentUserId) {
        api.saveUserFolders(currentUserId, next).catch(() => {})
        movedSessions.forEach((sess) => {
          api.saveUserSession(currentUserId, sess).catch(() => {})
        })
      }
      return next
    })
  }

  // Update workspace settings & user profile (isolated per user + persisted to SQLite users table)
  function handleSaveSettings(nextSettings) {
    const owner = currentUserId || 'admin'
    setWorkspaceSettings(nextSettings)
    saveStoredSettings(nextSettings, owner)
    if (nextSettings?.profile) {
      setUserProfile(nextSettings.profile)
      saveStoredUser(nextSettings.profile, owner)
      if (currentUserId) {
        api.updateUserProfile(currentUserId, nextSettings.profile).catch(() => {})
      }
    }
  }

  // Clear all sessions for current user only
  function handleClearAllSessions() {
    const fresh = createNewSession('f-general', 'New Query Session')
    setSessions([fresh])
    setActiveSessionId(fresh.id)
    if (currentUserId) {
      api
        .clearUserSessions(currentUserId)
        .then(() => api.saveUserSession(currentUserId, fresh))
        .catch(() => {})
    }
  }

  // Submit query in the active session
  async function submit(value = question) {
    const clean = value.trim()
    if (!clean || loading || !activeSession || !currentUserId) return
    setQuestion('')

    const targetSessionId = activeSession.id
    const targetUserId = currentUserId

    // Append user message & only auto-title if the user hasn't already named this session
    const updatedMessagesWithUser = [
      ...(activeSession.messages || []),
      { role: 'user', text: clean },
    ]

    const autoTitle = clean.length > 40 ? `${clean.slice(0, 40)}…` : clean
    const shouldAutoTitle = (sess) =>
      !sess.customTitle &&
      (sess.messages?.length || 0) === 0 &&
      (!sess.title || sess.title === 'New Query Session')

    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== targetSessionId) return s
        const updated = {
          ...s,
          title: shouldAutoTitle(s) ? autoTitle : s.title,
          messages: updatedMessagesWithUser,
          lastUpdated: Date.now(),
        }
        api.saveUserSession(targetUserId, updated).catch(() => {})
        return updated
      })
    )

    setLoading(true)

    try {
      const enableLivePubMed = workspaceSettings?.general?.enableLivePubMed ?? true

      const history = (activeSession.messages || [])
        .map((m) => ({
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.role === 'assistant' ? (m.result?.answer || m.text || '') : (m.text || ''),
        }))
        .filter((h) => h.content)

      const result = await api.chat({
        session_id: targetSessionId,
        user_id: targetUserId,
        question: clean,
        mode: effectiveMode,
        enable_live_pubmed: enableLivePubMed,
        history: history.slice(-6),
      })

      if (workspaceOwnerRef.current === targetUserId) {
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== targetSessionId) return s
            // Preserve the latest s.title, s.customTitle, and s.folderId in case user renamed/moved while loading
            const updated = {
              ...s,
              messages: [...updatedMessagesWithUser, { role: 'assistant', result }],
              lastUpdated: Date.now(),
            }
            api.saveUserSession(targetUserId, updated).catch(() => {})
            return updated
          })
        )
      }
    } catch (error) {
      const detail =
        error.response?.data?.detail || 'The assistant could not reach the research API.'
      if (workspaceOwnerRef.current === targetUserId) {
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== targetSessionId) return s
            const updated = {
              ...s,
              messages: [...updatedMessagesWithUser, { role: 'error', text: detail }],
              lastUpdated: Date.now(),
            }
            api.saveUserSession(targetUserId, updated).catch(() => {})
            return updated
          })
        )
      }
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
        theme={activeTheme}
        onToggleTheme={handleToggleTheme}
      />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Navigation Sidebar with Workspaces & Sessions */}
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          view={effectiveView}
          setView={setView}
          folders={folders}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
          onNewSession={handleNewSession}
          onMoveSession={handleMoveSession}
          onRenameSession={handleUpdateSessionTitle}
          onOpenFolderModal={() => setFolderModalOpen(true)}
          onDeleteSession={handleDeleteSession}
          onDeleteFolder={handleDeleteFolder}
          onOpenTriad={() => setTriadModalOpen(true)}
          mode={effectiveMode}
          setMode={setMode}
          isAdmin={isAdmin}
          researchMode={effectiveResearchMode}
          onToggleResearchMode={handleToggleResearchMode}
          userProfile={userProfile}
          onOpenSettings={() => setSettingsModalOpen(true)}
          onSignOut={handleSignOut}
        />

        {/* Main Body: Center Copilot Chat Area takes the stage */}
        <main className="flex flex-1 min-h-0 min-w-0 overflow-hidden">
          {effectiveView === 'evaluation' ? (
            <div className="flex-1 overflow-y-auto">
              <EvaluationView
                summary={summary}
                loading={summaryLoading}
                onRefresh={refreshSummary}
                onBackToChat={() => setView('chat')}
              />
            </div>
          ) : (
            <div className="flex-1 min-w-0 h-full">
              <ChatPane
                messages={activeSession?.messages || []}
                question={question}
                setQuestion={setQuestion}
                submit={submit}
                loading={loading}
                mode={effectiveMode}
                researchMode={effectiveResearchMode}
                density={workspaceSettings?.general?.density || 'default'}
                showShortcuts={workspaceSettings?.general?.showShortcuts ?? true}
                endRef={endRef}
                onOpenTriad={() => setTriadModalOpen(true)}
                activeFolder={folders?.find((f) => f.id === activeSession?.folderId) || folders?.[0]}
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
        userId={currentUserId || 'admin'}
        userProfile={userProfile}
        workspaceSettings={workspaceSettings}
        onSaveSettings={handleSaveSettings}
        sessionsCount={sessions.length}
        onClearAllSessions={handleClearAllSessions}
        onOpenEvaluation={handleOpenEvaluation}
        isAdmin={isAdmin}
      />

      {/* Role-Based Sign In Modal */}
      <AuthModal
        isOpen={!authSession?.isAuthenticated}
        onLogin={handleSignIn}
      />
    </div>
  )
}
