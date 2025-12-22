import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Faction Warfare API
export const factionWarfareApi = {
  getOverview: () => api.get('/faction-warfare/overview'),
  getTrends: (hours: number = 24) => api.get(`/faction-warfare/trends?hours=${hours}`),
  getLiveData: () => api.get('/faction-warfare/live'),
  getLeaderboards: () => api.get('/faction-warfare/leaderboards'),
}

// Systems API
export const systemsApi = {
  getSystems: (factionId?: number, contestedOnly?: boolean) => {
    const params = new URLSearchParams()
    if (factionId) params.append('faction_id', factionId.toString())
    if (contestedOnly) params.append('contested_only', 'true')
    return api.get(`/systems/?${params.toString()}`)
  },
  getSystemDetails: (systemId: number) => api.get(`/systems/${systemId}`),
  getSystemTrends: (systemId: number, hours: number = 24) => 
    api.get(`/systems/${systemId}/trends?hours=${hours}`),
  getSystemLiveData: (systemId: number) => api.get(`/systems/${systemId}/live`),
  getSystemKillmailStats: (systemId: number, timeWindowHours: number = 24) => 
    api.get(`/systems/${systemId}/killmail-stats?time_window_hours=${timeWindowHours}`),
  getStagedCorporations: (systemId: number, timeWindowHours: number = 168) => 
    api.get(`/systems/${systemId}/staged-corporations?time_window_hours=${timeWindowHours}`),
  getAllCorporationStagingSystems: (timeWindowHours: number = 168) => 
    api.get(`/systems/staging-systems/all?time_window_hours=${timeWindowHours}`),
  getContestedSystems: () => api.get('/systems/contested/'),
  getSystemsByFaction: (factionId: number) => api.get(`/systems/faction/${factionId}`),
}

// Frontlines API
export const frontlinesApi = {
  getOverview: () => api.get('/frontlines/'),
  getLiveData: () => api.get('/frontlines/live'),
  getSystemInfo: (systemId: number) => api.get(`/frontlines/system/${systemId}`),
  getSystemAdjacency: (systemId: number) => api.get(`/frontlines/adjacency/${systemId}`),
  getStatistics: () => api.get('/frontlines/stats'),
}

// Kills API
export const killsApi = {
  getStatistics: (params: {
    systemId?: number
    factionId?: number
    corporationId?: number
    allianceId?: number
    periodType?: string
    hours?: number
  } = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString())
      }
    })
    return api.get(`/kills/statistics?${searchParams.toString()}`)
  },
  getRecentKills: (params: {
    systemId?: number
    factionId?: number
    hours?: number
    limit?: number
  } = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString())
      }
    })
    return api.get(`/kills/recent?${searchParams.toString()}`)
  },
  getSystemKillStatistics: (systemId: number, hours: number = 24) =>
    api.get(`/kills/system/${systemId}?hours=${hours}`),
  getFactionKillStatistics: (factionId: number, hours: number = 24) =>
    api.get(`/kills/faction/${factionId}?hours=${hours}`),
  getKillTrends: (params: {
    factionId?: number
    systemId?: number
    hours?: number
  } = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString())
      }
    })
    return api.get(`/kills/trends?${searchParams.toString()}`)
  },
}

export default api
