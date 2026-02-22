import { useQuery } from '@tanstack/react-query'
import { 
  FileText, 
  Database, 
  Users, 
  TrendingUp, 
  Loader2, 
  AlertCircle 
} from 'lucide-react'
import { paperApi } from '../services/api'

export default function StatsPage() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: () => paperApi.getStats(),
    staleTime: 5 * 60 * 1000
  })

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-primary-600 animate-spin mb-4" />
        <p className="text-gray-600">Загружаем статистику...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertCircle className="w-10 h-10 text-red-500 mb-4" />
        <p className="text-gray-600">Ошибка при загрузке статистики</p>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Статистика базы данных</h1>

      {/* Main Stats */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Всего статей</p>
              <p className="text-3xl font-bold text-gray-900">
                {stats?.total_papers.toLocaleString() || '0'}
              </p>
            </div>
            <div className="w-12 h-12 bg-primary-50 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-primary-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">С полным текстом</p>
              <p className="text-3xl font-bold text-gray-900">
                {stats?.with_full_text.toLocaleString() || '0'}
              </p>
            </div>
            <div className="w-12 h-12 bg-green-50 rounded-xl flex items-center justify-center">
              <Database className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Покрытие</p>
              <p className="text-3xl font-bold text-gray-900">
                {stats?.processing_coverage.toFixed(1) || '0'}%
              </p>
            </div>
            <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Источников</p>
              <p className="text-3xl font-bold text-gray-900">
                {stats ? Object.keys(stats.by_source).length : '0'}
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* By Source */}
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">По источникам</h2>
          {stats?.by_source && Object.entries(stats.by_source).length > 0 ? (
            <div className="space-y-4">
              {Object.entries(stats.by_source)
                .sort((a, b) => b[1] - a[1])
                .map(([source, count]) => (
                  <div key={source}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700 capitalize">{source}</span>
                      <span className="text-gray-900 font-medium">{count.toLocaleString()}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all"
                        style={{
                          width: `${Math.min(100, (count / (stats?.total_papers || 1)) * 100)}%`
                        }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-gray-500">Нет данных</p>
          )}
        </div>

        {/* By Year */}
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">По годам</h2>
          {stats?.by_year && Object.entries(stats.by_year).length > 0 ? (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {Object.entries(stats.by_year)
                .sort((a, b) => parseInt(b[0]) - parseInt(a[0]))
                .slice(0, 20)
                .map(([year, count]) => (
                  <div key={year} className="flex justify-between items-center">
                    <span className="text-gray-700">{year}</span>
                    <div className="flex items-center">
                      <div className="w-32 bg-gray-200 rounded-full h-2 mr-3">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{
                            width: `${Math.min(100, (count / Math.max(...Object.values(stats.by_year))) * 100)}%`
                          }}
                        />
                      </div>
                      <span className="text-gray-900 font-medium w-16 text-right">
                        {count.toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-gray-500">Нет данных</p>
          )}
        </div>
      </div>

      {/* About Data */}
      <div className="mt-8 card bg-primary-50 border-primary-100">
        <h3 className="text-lg font-semibold text-primary-900 mb-2">
          О наших данных
        </h3>
        <p className="text-primary-700">
          Мы собираем публикации из открытых источников, включая eLibrary, CyberLeninka, 
          arXiv и репозитории российских университетов. Все данные регулярно обновляются 
          и индексируются для обеспечения качественного поиска.
        </p>
      </div>
    </div>
  )
}
