const STORAGE_SESSIONS_PREFIX = 'neuroevidence_sessions_v1'
const STORAGE_FOLDERS_PREFIX = 'neuroevidence_folders_v1'
const STORAGE_USER_PREFIX = 'neuroevidence_user_v1'
const STORAGE_SETTINGS_PREFIX = 'neuroevidence_settings_v1'
const STORAGE_AUTH_KEY = 'neuroevidence_auth_v1'

export const DEFAULT_FOLDERS = [
  { id: 'f-general', name: 'General Inquiries', color: '#0E6B70' },
  { id: 'f-pd', name: "Parkinson's Disease", color: '#4F46E5' },
  { id: 'f-epi', name: 'Epilepsy & Seizures', color: '#059669' },
]

export const DEMO_ACCOUNTS = {
  admin: {
    userId: 'admin',
    accountRole: 'admin',
    username: 'admin',
    password: 'admin123',
    profile: {
      name: 'Daniel Puah',
      role: 'Researcher / Developer (Admin)',
      email: 'admin@neuroevidence.edu',
      specialty: 'Clinical Informatics & Neurology',
      institution: 'NeuroEvidence Research Lab',
    },
  },
  clinician: {
    userId: 'puah',
    accountRole: 'clinician',
    username: 'Puah',
    password: 'puah123',
    profile: {
      name: 'Puah',
      role: 'Clinician / Medical Learner',
      email: 'puah@neuroevidence.edu',
      specialty: 'Movement Disorders & Epilepsy',
      institution: 'Neurology Teaching Hospital',
    },
  },
}

export const DEFAULT_USER = {
  ...DEMO_ACCOUNTS.admin.profile,
}

export const DEFAULT_SETTINGS = {
  general: {
    theme: 'light',
    density: 'default',
    autoScroll: true,
    showShortcuts: true,
    enableLivePubMed: true,
  },
  profile: {
    ...DEFAULT_USER,
  },
}

function normalizeUserId(userId) {
  return (userId || 'admin').toString().trim().toLowerCase().replace(/[^a-z0-9._-]/g, '_') || 'admin'
}

function scopedKey(prefix, userId) {
  return `${prefix}_${normalizeUserId(userId)}`
}

export function getDefaultProfileForUser(userId) {
  const norm = normalizeUserId(userId)
  if (norm === 'admin') return { ...DEMO_ACCOUNTS.admin.profile }
  if (norm === 'puah') return { ...DEMO_ACCOUNTS.clinician.profile }
  return {
    name: userId || 'Clinician User',
    role: 'Clinician / Medical Learner',
    email: `${norm}@neuroevidence.edu`,
    specialty: 'Neurology',
    institution: 'Neurology Teaching Hospital',
  }
}

export function getStoredFolders(userId = 'admin') {
  const norm = normalizeUserId(userId)
  try {
    const raw = localStorage.getItem(scopedKey(STORAGE_FOLDERS_PREFIX, norm))
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length > 0) return parsed
    }
    // One-time migration of legacy un-scoped folders into admin only
    if (norm === 'admin') {
      const legacy = localStorage.getItem(STORAGE_FOLDERS_PREFIX)
      if (legacy) {
        const parsed = JSON.parse(legacy)
        if (Array.isArray(parsed) && parsed.length > 0) {
          localStorage.setItem(scopedKey(STORAGE_FOLDERS_PREFIX, norm), legacy)
          return parsed
        }
      }
    }
  } catch (e) {
    console.error('Error loading folders:', e)
  }
  return DEFAULT_FOLDERS.map((f) => ({ ...f }))
}

export function saveStoredFolders(folders, userId = 'admin') {
  try {
    localStorage.setItem(scopedKey(STORAGE_FOLDERS_PREFIX, userId), JSON.stringify(folders))
  } catch (e) {
    console.error('Error saving folders:', e)
  }
}

export function getStoredSessions(userId = 'admin') {
  const norm = normalizeUserId(userId)
  try {
    const raw = localStorage.getItem(scopedKey(STORAGE_SESSIONS_PREFIX, norm))
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed
    }
    // One-time migration of legacy un-scoped sessions into admin only
    if (norm === 'admin') {
      const legacy = localStorage.getItem(STORAGE_SESSIONS_PREFIX)
      if (legacy) {
        const parsed = JSON.parse(legacy)
        if (Array.isArray(parsed) && parsed.length > 0) {
          localStorage.setItem(scopedKey(STORAGE_SESSIONS_PREFIX, norm), legacy)
          return parsed
        }
      }
    }
  } catch (e) {
    console.error('Error loading sessions:', e)
  }
  return []
}

export function saveStoredSessions(sessions, userId = 'admin') {
  try {
    localStorage.setItem(scopedKey(STORAGE_SESSIONS_PREFIX, userId), JSON.stringify(sessions))
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

export function getStoredAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_AUTH_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (typeof parsed?.isAuthenticated === 'boolean') {
        const accountRole =
          parsed.accountRole === 'admin'
            ? 'admin'
            : parsed.accountRole === 'clinician'
            ? 'clinician'
            : null
        const userId =
          parsed.userId ||
          (accountRole === 'admin' ? 'admin' : accountRole === 'clinician' ? 'puah' : null)
        return {
          isAuthenticated: parsed.isAuthenticated,
          accountRole,
          userId,
        }
      }
    }
  } catch (e) {
    console.error('Error loading auth state:', e)
  }
  return { isAuthenticated: true, accountRole: 'admin', userId: 'admin' }
}

export function saveStoredAuth(authState) {
  try {
    localStorage.setItem(STORAGE_AUTH_KEY, JSON.stringify(authState))
  } catch (e) {
    console.error('Error saving auth state:', e)
  }
}

export function authenticateUser({ identifier, password }) {
  const cleanId = (identifier || '').trim().toLowerCase()
  const cleanPassword = (password || '').trim()

  if (!cleanId || !cleanPassword) {
    return { ok: false, error: 'Please enter both username/email and password.' }
  }

  // Check Admin credentials
  if (
    (cleanId === DEMO_ACCOUNTS.admin.username.toLowerCase() ||
      cleanId === DEMO_ACCOUNTS.admin.profile.email.toLowerCase()) &&
    cleanPassword === DEMO_ACCOUNTS.admin.password
  ) {
    return {
      ok: true,
      userId: DEMO_ACCOUNTS.admin.userId,
      accountRole: 'admin',
      profile: { ...DEMO_ACCOUNTS.admin.profile },
    }
  }

  // Check Normal Clinician credentials
  if (
    (cleanId === DEMO_ACCOUNTS.clinician.username.toLowerCase() ||
      cleanId === DEMO_ACCOUNTS.clinician.profile.email.toLowerCase()) &&
    cleanPassword === DEMO_ACCOUNTS.clinician.password
  ) {
    return {
      ok: true,
      userId: DEMO_ACCOUNTS.clinician.userId,
      accountRole: 'clinician',
      profile: { ...DEMO_ACCOUNTS.clinician.profile },
    }
  }

  return {
    ok: false,
    error: 'Invalid username or password.',
  }
}

export function getStoredSettings(userId = 'admin') {
  const defaultProfile = getDefaultProfileForUser(userId)
  try {
    const raw = localStorage.getItem(scopedKey(STORAGE_SETTINGS_PREFIX, userId))
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        general: {
          ...DEFAULT_SETTINGS.general,
          ...(parsed?.general || {}),
        },
        profile: {
          ...defaultProfile,
          ...(parsed?.profile || {}),
        },
      }
    }
  } catch (e) {
    console.error('Error loading settings:', e)
  }
  return {
    general: { ...DEFAULT_SETTINGS.general },
    profile: defaultProfile,
  }
}

export function saveStoredSettings(settings, userId = 'admin') {
  try {
    localStorage.setItem(scopedKey(STORAGE_SETTINGS_PREFIX, userId), JSON.stringify(settings))
  } catch (e) {
    console.error('Error saving settings:', e)
  }
}

export function getStoredUser(userId = 'admin') {
  const defaultProfile = getDefaultProfileForUser(userId)
  try {
    const raw = localStorage.getItem(scopedKey(STORAGE_USER_PREFIX, userId))
    if (raw) return { ...defaultProfile, ...JSON.parse(raw) }
    const settings = getStoredSettings(userId)
    if (settings?.profile) return settings.profile
  } catch (e) {
    console.error('Error loading user profile:', e)
  }
  return defaultProfile
}

export function saveStoredUser(user, userId = 'admin') {
  try {
    localStorage.setItem(scopedKey(STORAGE_USER_PREFIX, userId), JSON.stringify(user))
  } catch (e) {
    console.error('Error saving user profile:', e)
  }
}
