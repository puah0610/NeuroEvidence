const STORAGE_SESSIONS_KEY = 'neuroevidence_sessions_v1'
const STORAGE_FOLDERS_KEY = 'neuroevidence_folders_v1'

export const DEFAULT_FOLDERS = [
  { id: 'f-general', name: 'General Inquiries', color: '#0E6B70' },
  { id: 'f-pd', name: "Parkinson's Disease", color: '#4F46E5' },
  { id: 'f-epi', name: 'Epilepsy & Seizures', color: '#059669' },
]

export function getStoredFolders() {
  try {
    const raw = localStorage.getItem(STORAGE_FOLDERS_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) {
    console.error('Error loading folders:', e)
  }
  return DEFAULT_FOLDERS
}

export function saveStoredFolders(folders) {
  try {
    localStorage.setItem(STORAGE_FOLDERS_KEY, JSON.stringify(folders))
  } catch (e) {
    console.error('Error saving folders:', e)
  }
}

export function getStoredSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_SESSIONS_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) {
    console.error('Error loading sessions:', e)
  }
  return []
}

export function saveStoredSessions(sessions) {
  try {
    localStorage.setItem(STORAGE_SESSIONS_KEY, JSON.stringify(sessions))
  } catch (e) {
    console.error('Error saving sessions:', e)
  }
}

export function createNewSession(folderId = 'f-general', title = 'New Query Session') {
  return {
    id: `session-${crypto.randomUUID()}`,
    title,
    folderId,
    timestamp: Date.now(),
    lastUpdated: Date.now(),
    messages: [],
    mode: 'rag_verified',
  }
}

export function formatSessionTimestamp(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const isToday =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()

  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday =
    date.getDate() === yesterday.getDate() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getFullYear() === yesterday.getFullYear()

  const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  if (isToday) {
    return `Today at ${timeStr}`
  }
  if (isYesterday) {
    return `Yesterday at ${timeStr}`
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const STORAGE_USER_KEY = 'neuroevidence_user_v1'

export const DEFAULT_USER = {
  name: 'Daniel Puah',
  role: 'Medical Student / Researcher',
  email: 'daniel.puah@university.edu',
  specialty: 'Neurology & Neurotherapeutics',
  institution: 'School of Medicine / University Health',
}

const STORAGE_SETTINGS_KEY = 'neuroevidence_settings_v1'

export const DEFAULT_SETTINGS = {
  general: {
    theme: 'light',
    density: 'default',
    autoScroll: true,
    showShortcuts: true,
    language: 'en-US',
    enableLivePubMed: true,
  },
  profile: {
    ...DEFAULT_USER,
  },
  notifications: {
    safetyAlerts: true,
    triadUpdates: true,
    soundAlerts: false,
    emailDigest: false,
  },
  voice: {
    voiceInput: true,
    ttsVoice: 'nova',
    speechRate: '1.0',
    autoRead: false,
  },
  analytics: {
    recordTraces: true,
    latencyTracking: true,
    anonymizedTelemetry: true,
  },
  storage: {
    retention: 'never',
  },
}

export function getStoredSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_SETTINGS_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) {
    console.error('Error loading settings:', e)
  }
  return DEFAULT_SETTINGS
}

export function saveStoredSettings(settings) {
  try {
    localStorage.setItem(STORAGE_SETTINGS_KEY, JSON.stringify(settings))
  } catch (e) {
    console.error('Error saving settings:', e)
  }
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(STORAGE_USER_KEY)
    if (raw) return JSON.parse(raw)
    const settings = getStoredSettings()
    if (settings?.profile) return settings.profile
  } catch (e) {
    console.error('Error loading user profile:', e)
  }
  return DEFAULT_USER
}

export function saveStoredUser(user) {
  try {
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user))
  } catch (e) {
    console.error('Error saving user profile:', e)
  }
}

