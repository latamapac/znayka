import axios from 'axios'
import type { Paper, SearchResponse, IndexStats, SearchFilters } from '../types/paper'

const API_BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const paperApi = {
  // Search papers
  search: async (
    query: string,
    options: {
      limit?: number
      offset?: number
      searchType?: string
      filters?: SearchFilters
    } = {}
  ): Promise<SearchResponse> => {
    const { limit = 20, offset = 0, searchType = 'hybrid', filters } = options
    
    const params = new URLSearchParams({
      q: query,
      limit: String(limit),
      offset: String(offset),
      search_type: searchType,
    })
    
    if (filters?.year_from) params.append('year_from', String(filters.year_from))
    if (filters?.year_to) params.append('year_to', String(filters.year_to))
    if (filters?.source) params.append('source', filters.source)
    if (filters?.journal) params.append('journal', filters.journal)
    
    const response = await api.get(`/papers/search?${params}`)
    return response.data
  },

  // Semantic search
  semanticSearch: async (
    query: string,
    options: {
      limit?: number
      offset?: number
      filters?: SearchFilters
    } = {}
  ): Promise<SearchResponse> => {
    const response = await api.post('/papers/semantic-search', {
      query,
      limit: options.limit || 20,
      offset: options.offset || 0,
      filters: options.filters,
    })
    return response.data
  },

  // Get paper by ID
  getById: async (id: string): Promise<Paper> => {
    const response = await api.get(`/papers/${id}`)
    return response.data
  },

  // Get similar papers
  getSimilar: async (id: string, limit: number = 10): Promise<Paper[]> => {
    const response = await api.get(`/papers/${id}/similar?limit=${limit}`)
    return response.data.papers
  },

  // Get index stats
  getStats: async (): Promise<IndexStats> => {
    const response = await api.get('/papers/stats/index')
    return response.data
  },
}

export default api
