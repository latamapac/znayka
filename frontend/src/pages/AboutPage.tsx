import { BookOpen, Github, Heart, Users, Globe, Database } from 'lucide-react'

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-russia-blue to-primary-600 rounded-2xl flex items-center justify-center">
          <BookOpen className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          О проекте
        </h1>
        <p className="text-xl text-gray-600">
          Российский Научный Хаб — студенческий проект с открытым исходным кодом
        </p>
      </div>

      {/* Mission */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Наша миссия</h2>
        <div className="card">
          <p className="text-gray-700 mb-4 leading-relaxed">
            Мы создаем единую открытую платформу для поиска и анализа российских 
            научных публикаций. Наша цель — сделать научные знания доступными для 
            студентов, исследователей и всех, кто интересуется наукой.
          </p>
          <p className="text-gray-700 leading-relaxed">
            Проект объединяет данные из множества источников и предоставляет 
            современные инструменты поиска, включая семантический поиск на основе 
            искусственного интеллекта.
          </p>
        </div>
      </section>

      {/* Features Grid */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Что мы предлагаем</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="card text-center">
            <Database className="w-10 h-10 text-primary-600 mx-auto mb-4" />
            <h3 className="font-semibold text-gray-900 mb-2">Единая база</h3>
            <p className="text-gray-600 text-sm">
              Интеграция с eLibrary, CyberLeninka, arXiv и университетскими репозиториями
            </p>
          </div>
          <div className="card text-center">
            <Globe className="w-10 h-10 text-primary-600 mx-auto mb-4" />
            <h3 className="font-semibold text-gray-900 mb-2">Уникальная индексация</h3>
            <p className="text-gray-600 text-sm">
              Каждой статье присваивается уникальный идентификатор RSH
            </p>
          </div>
          <div className="card text-center">
            <Users className="w-10 h-10 text-primary-600 mx-auto mb-4" />
            <h3 className="font-semibold text-gray-900 mb-2">Open Source</h3>
            <p className="text-gray-600 text-sm">
              Открытый исходный код и свободный доступ для всех
            </p>
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Технологии</h2>
        <div className="card">
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Backend</h3>
              <ul className="space-y-2 text-gray-600">
                <li>• FastAPI (Python)</li>
                <li>• PostgreSQL + pgvector</li>
                <li>• SQLAlchemy + Alembic</li>
                <li>• Sentence Transformers</li>
                <li>• Celery + Redis</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Frontend</h3>
              <ul className="space-y-2 text-gray-600">
                <li>• React 18 + TypeScript</li>
                <li>• Tailwind CSS</li>
                <li>• TanStack Query</li>
                <li>• Vite</li>
                <li>• Zustand</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Команда</h2>
        <div className="card">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
              <Users className="w-8 h-8 text-primary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Студенческая команда</h3>
              <p className="text-gray-600">
                Мы — группа студентов, увлеченных развитием науки и технологий в России.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Contact / GitHub */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Присоединяйтесь</h2>
        <div className="flex flex-col sm:flex-row gap-4">
          <a
            href="https://github.com/your-org/russian-science-hub"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary flex items-center justify-center"
          >
            <Github className="w-5 h-5 mr-2" />
            GitHub
          </a>
        </div>
        <p className="mt-6 text-center text-gray-500 flex items-center justify-center">
          Сделано с <Heart className="w-4 h-4 mx-1 text-red-500" /> для развития российской науки
        </p>
      </section>
    </div>
  )
}
