import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 90000,
})

export const api = {
  chat: async (payload) => (await client.post('/api/chat', payload)).data,
  feedback: async (payload) => (await client.post('/api/feedback', payload)).data,
  summary: async () => (await client.get('/api/evaluation/summary')).data,
  health: async () => (await client.get('/api/health')).data,
}

