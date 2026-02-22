import { useState, FormEvent } from 'react'
import { Search, Loader2 } from 'lucide-react'

interface SearchBarProps {
  onSearch: (query: string, searchType: string) => void
  isLoading?: boolean
  initialQuery?: string
  className?: string
}

export default function SearchBar({
  onSearch,
  isLoading = false,
  initialQuery = '',
  className = ''
}: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery)
  const [searchType, setSearchType] = useState('hybrid')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query.trim(), searchType)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={`w-full ${className}`}>
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search Input */}
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск научных статей..."
            className="input pl-12 py-4 text-lg"
            disabled={isLoading}
          />
        </div>

        {/* Search Type Select */}
        <select
          value={searchType}
          onChange={(e) => setSearchType(e.target.value)}
          className="input py-4 sm:w-48"
          disabled={isLoading}
        >
          <option value="hybrid">Гибридный поиск</option>
          <option value="text">По тексту</option>
          <option value="semantic">Семантический</option>
        </select>

        {/* Search Button */}
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="btn-primary py-4 px-8 flex items-center justify-center space-x-2 disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Поиск...</span>
            </>
          ) : (
            <span>Поиск</span>
          )}
        </button>
      </div>

      {/* Search Tips */}
      <div className="mt-3 flex flex-wrap gap-2 text-sm text-gray-500">
        <span>Попробуйте:</span>
        {['машинное обучение', 'квантовые вычисления', 'биотехнологии', 'материаловедение'].map((term) => (
          <button
            key={term}
            type="button"
            onClick={() => setQuery(term)}
            className="text-primary-600 hover:text-primary-700 hover:underline"
          >
            {term}
          </button>
        ))}
      </div>
    </form>
  )
}
