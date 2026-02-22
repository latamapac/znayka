export interface Author {
  id: string
  full_name: string
  full_name_ru?: string
  affiliations?: string[]
  orcid?: string
}

export interface Paper {
  id: string
  title: string
  title_ru?: string
  abstract?: string
  abstract_ru?: string
  doi?: string
  arxiv_id?: string
  source_type: string
  source_url?: string
  journal?: string
  journal_ru?: string
  publisher?: string
  volume?: string
  issue?: string
  pages?: string
  publication_year?: number
  publication_date?: string
  keywords?: string[]
  keywords_ru?: string[]
  authors: Author[]
  citation_count: number
  citation_count_rsci: number
  pdf_url?: string
  language: string
  crawled_at: string
  updated_at: string
}

export interface SearchResponse {
  papers: Paper[]
  total: number
  limit: number
  offset: number
  search_type: string
}

export interface SearchFilters {
  year_from?: number
  year_to?: number
  source?: string
  journal?: string
  has_full_text?: boolean
  language?: string
}

export interface IndexStats {
  total_papers: number
  by_source: Record<string, number>
  by_year: Record<string, number>
  with_full_text: number
  processing_coverage: number
}
