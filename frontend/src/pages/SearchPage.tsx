import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import SearchBar from '../components/SearchBar'
import PaperCard from '../components/PaperCard'
import { paperApi } from '../services/api'
import type { Paper, SearchFilters } from '../types/paper'

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(0)
  const limit = 20

  const query = searchParams.get('q') || ''
  const searchType = searchParams.get('type') || 'hybrid'

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['search', query, searchType, page],
    queryFn: () => paperApi.search(query, {
      limit,
      offset: page * limit,
      searchType
    }),
    enabled: query.length > 0,
    staleTime: 5 * 60 * 1000
  })

  const handleSearch = (newQuery: string, newSearchType: string) => {
    setPage(0)
    setSearchParams({ q: newQuery, type: newSearchType })
  }

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Search Header */}
      <div className="bg-white border-b border-gray-200 sticky top-16 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <SearchBar
            onSearch={handleSearch}
            initialQuery={query}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Results */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!query ? (
          <div className="text-center py-20">
            <p className="text-gray-500 text-lg">
              Введите поисковый запрос, чтобы найти научные статьи
            </p>
          </div>
        ) : isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-10 h-10 text-primary-600 animate-spin mb-4" />
            <p className="text-gray-600">Ищем статьи...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20">
            <AlertCircle className="w-10 h-10 text-red-500 mb-4" />
            <p className="text-gray-600">Ошибка при поиске. Попробуйте позже.</p>
          </div>
        ) : data && data.papers.length > 0 ? (
          <>
            {/* Results Header */}
            <div className="flex items-center justify-between mb-6">
              <p className="text-gray-600">
                Найдено <span className="font-semibold text-gray-900">{data.total}</span> результатов
                {query && (
                  <span> по запросу "<span className="font-medium">{query}</span>"</span>
                )}
              </p>
              <span className="text-sm text-gray-500">
                Тип поиска: {searchType === 'hybrid' ? 'Гибридный' : 
                           searchType === 'semantic' ? 'Семантический' : 'Текстовый'}
              </span>
            </div>

            {/* Paper Cards */}
            <div className="space-y-4">
              {data.papers.map((paper) => (
                <PaperCard key={paper.id} paper={paper} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center mt-8 space-x-4">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="btn-secondary flex items-center disabled:opacity-50"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Назад
                </button>
                
                <span className="text-gray-600">
                  Страница {page + 1} из {totalPages}
                </span>
                
                <button
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="btn-secondary flex items-center disabled:opacity-50"
                >
                  Вперед
                  <ChevronRight className="w-4 h-4 ml-1" />
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-500 text-lg mb-2">
              По запросу "{query}" ничего не найдено
            </p>
            <p className="text-gray-400">
              Попробуйте изменить поисковый запрос или использовать другие ключевые слова
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
