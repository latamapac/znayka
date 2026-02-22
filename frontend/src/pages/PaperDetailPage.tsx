import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  ArrowLeft, 
  Calendar, 
  Users, 
  BookOpen, 
  ExternalLink, 
  FileText,
  Quote,
  Loader2,
  AlertCircle
} from 'lucide-react'
import { paperApi } from '../services/api'
import PaperCard from '../components/PaperCard'

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: paper, isLoading, error } = useQuery({
    queryKey: ['paper', id],
    queryFn: () => paperApi.getById(id!),
    enabled: !!id
  })

  const { data: similarPapers } = useQuery({
    queryKey: ['similar', id],
    queryFn: () => paperApi.getSimilar(id!, 5),
    enabled: !!id
  })

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-primary-600 animate-spin mb-4" />
        <p className="text-gray-600">Загружаем информацию о статье...</p>
      </div>
    )
  }

  if (error || !paper) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <AlertCircle className="w-10 h-10 text-red-500 mb-4" />
        <p className="text-gray-600">Статья не найдена или произошла ошибка</p>
        <Link to="/search" className="btn-primary mt-4">
          Вернуться к поиску
        </Link>
      </div>
    )
  }

  const displayTitle = paper.title_ru || paper.title
  const displayAbstract = paper.abstract_ru || paper.abstract

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Link */}
      <Link
        to="/search"
        className="inline-flex items-center text-gray-600 hover:text-primary-600 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Назад к поиску
      </Link>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2">
          <article className="card">
            {/* Title */}
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-tight mb-6">
              {displayTitle}
            </h1>

            {/* Authors */}
            {paper.authors && paper.authors.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-medium text-gray-500 mb-2 flex items-center">
                  <Users className="w-4 h-4 mr-2" />
                  Авторы
                </h2>
                <div className="flex flex-wrap gap-2">
                  {paper.authors.map((author, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-sm"
                    >
                      {author.full_name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata */}
            <div className="flex flex-wrap gap-4 mb-6 text-sm">
              {paper.publication_year && (
                <span className="flex items-center text-gray-600">
                  <Calendar className="w-4 h-4 mr-1" />
                  {paper.publication_year}
                </span>
              )}
              {paper.journal && (
                <span className="flex items-center text-gray-600">
                  <BookOpen className="w-4 h-4 mr-1" />
                  {paper.journal}
                </span>
              )}
              {paper.citation_count > 0 && (
                <span className="flex items-center text-gray-600">
                  <Quote className="w-4 h-4 mr-1" />
                  {paper.citation_count} цитирований
                </span>
              )}
              <span className="badge-green">
                {paper.source_type}
              </span>
            </div>

            {/* Abstract */}
            {displayAbstract && (
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Аннотация</h2>
                <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {displayAbstract}
                </p>
              </div>
            )}

            {/* Keywords */}
            {((paper.keywords && paper.keywords.length > 0) || (paper.keywords_ru && paper.keywords_ru.length > 0)) && (
              <div className="mb-6">
                <h2 className="text-sm font-medium text-gray-500 mb-2">Ключевые слова</h2>
                <div className="flex flex-wrap gap-2">
                  {[...(paper.keywords || []), ...(paper.keywords_ru || [])].map((keyword, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-primary-50 text-primary-700 rounded-full text-sm"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Links */}
            <div className="flex flex-wrap gap-3 pt-6 border-t border-gray-200">
              {paper.pdf_url && (
                <a
                  href={paper.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary flex items-center"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Открыть PDF
                </a>
              )}
              {paper.source_url && (
                <a
                  href={paper.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary flex items-center"
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Источник
                </a>
              )}
              {paper.doi && (
                <a
                  href={`https://doi.org/${paper.doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary flex items-center"
                >
                  DOI
                  <ExternalLink className="w-4 h-4 ml-2" />
                </a>
              )}
            </div>
          </article>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Paper Info */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Информация</h3>
            <dl className="space-y-3 text-sm">
              {paper.doi && (
                <div>
                  <dt className="text-gray-500">DOI</dt>
                  <dd className="font-mono text-gray-900">{paper.doi}</dd>
                </div>
              )}
              {paper.arxiv_id && (
                <div>
                  <dt className="text-gray-500">arXiv ID</dt>
                  <dd className="font-mono text-gray-900">{paper.arxiv_id}</dd>
                </div>
              )}
              <div>
                <dt className="text-gray-500">Источник</dt>
                <dd className="text-gray-900 capitalize">{paper.source_type}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Язык</dt>
                <dd className="text-gray-900">{paper.language === 'ru' ? 'Русский' : 'Английский'}</dd>
              </div>
              {paper.volume && (
                <div>
                  <dt className="text-gray-500">Том</dt>
                  <dd className="text-gray-900">{paper.volume}</dd>
                </div>
              )}
              {paper.issue && (
                <div>
                  <dt className="text-gray-500">Выпуск</dt>
                  <dd className="text-gray-900">{paper.issue}</dd>
                </div>
              )}
              {paper.pages && (
                <div>
                  <dt className="text-gray-500">Страницы</dt>
                  <dd className="text-gray-900">{paper.pages}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Similar Papers */}
          {similarPapers && similarPapers.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">Похожие статьи</h3>
              <div className="space-y-4">
                {similarPapers.map((paper) => (
                  <PaperCard key={paper.id} paper={paper} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
