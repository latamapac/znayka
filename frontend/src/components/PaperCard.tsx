import { Link } from 'react-router-dom'
import { Calendar, Users, BookOpen, ExternalLink, FileText } from 'lucide-react'
import type { Paper } from '../types/paper'

interface PaperCardProps {
  paper: Paper
}

export default function PaperCard({ paper }: PaperCardProps) {
  const displayTitle = paper.title_ru || paper.title
  const displayAbstract = paper.abstract_ru || paper.abstract

  return (
    <div className="card hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-lg font-semibold text-gray-900 leading-tight">
          <Link 
            to={`/paper/${paper.id}`}
            className="hover:text-primary-600 transition-colors"
          >
            {displayTitle}
          </Link>
        </h3>
        {paper.pdf_url && (
          <a
            href={paper.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 text-gray-400 hover:text-red-500 transition-colors"
            title="Открыть PDF"
          >
            <FileText className="w-5 h-5" />
          </a>
        )}
      </div>

      {/* Authors */}
      {paper.authors && paper.authors.length > 0 && (
        <div className="mt-3 flex items-center text-sm text-gray-600">
          <Users className="w-4 h-4 mr-2 flex-shrink-0" />
          <span className="line-clamp-1">
            {paper.authors.map(a => a.full_name).join(', ')}
          </span>
        </div>
      )}

      {/* Abstract */}
      {displayAbstract && (
        <p className="mt-3 text-gray-600 text-sm line-clamp-3">
          {displayAbstract}
        </p>
      )}

      {/* Footer */}
      <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
        {/* Year */}
        {paper.publication_year && (
          <span className="badge-gray flex items-center">
            <Calendar className="w-3 h-3 mr-1" />
            {paper.publication_year}
          </span>
        )}

        {/* Journal */}
        {paper.journal && (
          <span className="badge-blue flex items-center">
            <BookOpen className="w-3 h-3 mr-1" />
            {paper.journal.length > 30 
              ? paper.journal.slice(0, 30) + '...' 
              : paper.journal}
          </span>
        )}

        {/* Source */}
        <span className="badge-green">
          {paper.source_type}
        </span>

        {/* Citations */}
        {paper.citation_count > 0 && (
          <span className="text-gray-500">
            {paper.citation_count} цитирований
          </span>
        )}

        {/* DOI */}
        {paper.doi && (
          <a
            href={`https://doi.org/${paper.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-600 hover:text-primary-700 flex items-center"
          >
            DOI
            <ExternalLink className="w-3 h-3 ml-1" />
          </a>
        )}
      </div>

      {/* Keywords */}
      {paper.keywords && paper.keywords.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {paper.keywords.slice(0, 5).map((keyword, idx) => (
            <span
              key={idx}
              className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded"
            >
              {keyword}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
