const DEFAULT_API_URL = 'https://theme-trader.onrender.com'

export const API_URL = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, '')

const wsFromApi = API_URL.replace(/^http/i, 'ws')
export const WS_URL = import.meta.env.VITE_WS_URL || `${wsFromApi}/ws/prices`
