import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.startsWith('/login')) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// Auth
export const login = (username: string, password: string) =>
  api.post('/auth/login', { username, password })

export const getMe = () => api.get('/auth/me')

export const changePassword = (old_password: string, new_password: string) =>
  api.post('/auth/change-password', { old_password, new_password })

// Dashboard
export const getDashboard = () => api.get('/dashboard')

// Instances
export const getInstances = (params?: { status?: string }) =>
  api.get('/instances', { params })

export const getInstance = (instanceId: string) =>
  api.get(`/instances/${instanceId}`)

export const deleteInstance = (instanceId: string) =>
  api.delete(`/instances/${instanceId}`)

export const deleteAgent = (agentId: string, instanceId: string) =>
  api.delete(`/agents/${agentId}`, { params: { instance_id: instanceId } })

// Agents
export const getAgents = (params?: { instance_id?: string }) =>
  api.get('/agents', { params })

export const getAgent = (agentId: string, instanceId: string) =>
  api.get(`/agents/${agentId}`, { params: { instance_id: instanceId } })

export const getAgentSessions = (agentId: string, params?: { instance_id?: string }) =>
  api.get(`/agents/${agentId}/sessions`, { params })

export const getAgentDocs = (agentId: string, instanceId: string) =>
  api.get(`/agents/${agentId}/docs`, { params: { instance_id: instanceId } })

// Sessions
export const getSessions = (params?: {
  instance_id?: string
  agent_id?: string
  channel?: string
  status?: string
  limit?: number
  offset?: number
}) => api.get('/sessions', { params })

// Tokens
export const getTokenSummary = () => api.get('/tokens/summary')

export const getTokenTrend = (params?: {
  range?: string
  instance_id?: string
  agent_id?: string
}) => api.get('/tokens/trend', { params })

// Ranks
export const getRanks = () => api.get('/ranks')
