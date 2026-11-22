import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 180000,
})

export const api = {
  chat: async (payload) => (await client.post('/api/chat', payload)).data,
  feedback: async (payload) => (await client.post('/api/feedback', payload)).data,
  summary: async () => (await client.get('/api/evaluation/summary')).data,
  health: async () => (await client.get('/api/health')).data,

  // Database-backed Authentication (SQLite users table + per-user data/users/<user_id>/)
  login: async (payload) => (await client.post('/api/auth/login', payload)).data,
  register: async (payload) => (await client.post('/api/auth/register', payload)).data,
  updateUserProfile: async (userId, profile) =>
    (await client.put(`/api/users/${encodeURIComponent(userId)}/profile`, profile)).data,

  // Per-user isolated workspace & session storage (data/users/<user_id>/)
  getUserWorkspace: async (userId) =>
    (await client.get(`/api/users/${encodeURIComponent(userId)}/workspace`)).data,
  saveUserFolders: async (userId, folders) =>
    (await client.put(`/api/users/${encodeURIComponent(userId)}/folders`, { folders })).data,
  saveUserSession: async (userId, session) =>
    (
      await client.put(
        `/api/users/${encodeURIComponent(userId)}/sessions/${encodeURIComponent(session.id)}`,
        session
      )
    ).data,
  deleteUserSession: async (userId, sessionId) =>
    (
      await client.delete(
        `/api/users/${encodeURIComponent(userId)}/sessions/${encodeURIComponent(sessionId)}`
      )
    ).data,
  clearUserSessions: async (userId) =>
    (await client.delete(`/api/users/${encodeURIComponent(userId)}/sessions`)).data,
}
