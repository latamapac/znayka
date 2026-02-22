import { Link } from 'react-router-dom'
import { Search, Database, Brain, Globe, ChevronRight, Sparkles } from 'lucide-react'
import SearchBar from '../components/SearchBar'

export default function HomePage() {
  const handleSearch = (query: string, searchType: string) => {
    const params = new URLSearchParams({
      q: query,
      type: searchType
    })
    window.location.href = `/search?${params}`
  }

  return (
    <div>
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-primary-600 via-primary-700 to-russia-blue py-20 sm:py-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center px-4 py-2 rounded-full bg-white/10 text-white text-sm mb-6">
            <Sparkles className="w-4 h-4 mr-2" />
            Студенческий проект для развития российской науки
          </div>
          
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-6">
            Все научные статьи России
            <span className="block text-primary-200">в одном месте</span>
          </h1>
          
          <p className="text-xl text-primary-100 mb-10 max-w-2xl mx-auto">
            Единая база данных академических публикаций с умным поиском, 
            семантическим анализом и уникальной индексацией
          </p>

          {/* Search Bar */}
          <div className="bg-white rounded-2xl p-4 shadow-2xl">
            <SearchBar onSearch={handleSearch} />
          </div>

          {/* Stats */}
          <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-6 text-white">
            <div>
              <div className="text-3xl font-bold">1M+</div>
              <div className="text-primary-200">Статей в базе</div>
            </div>
            <div>
              <div className="text-3xl font-bold">50+</div>
              <div className="text-primary-200">Источников</div>
            </div>
            <div>
              <div className="text-3xl font-bold">100K+</div>
              <div className="text-primary-200">Авторов</div>
            </div>
            <div>
              <div className="text-3xl font-bold">AI</div>
              <div className="text-primary-200">Поиск</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Почему наш проект?
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Мы создаем открытую платформу для поиска и анализа российских научных публикаций
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              {
                icon: Database,
                title: 'Единая база',
                description: 'Интеграция с eLibrary, CyberLeninka, arXiv и многими другими источниками'
              },
              {
                icon: Search,
                title: 'Умный поиск',
                description: 'Гибридный поиск по тексту и семантический поиск с использованием AI'
              },
              {
                icon: Brain,
                title: 'Семантический анализ',
                description: 'Поиск по смыслу, а не только по ключевым словам'
              },
              {
                icon: Globe,
                title: 'Открытый доступ',
                description: 'Бесплатный доступ к научным знаниям для всех'
              }
            ].map((feature, idx) => {
              const Icon = feature.icon
              return (
                <div key={idx} className="card text-center group hover:border-primary-300 transition-colors">
                  <div className="w-14 h-14 mx-auto mb-4 bg-primary-50 rounded-xl flex items-center justify-center group-hover:bg-primary-100 transition-colors">
                    <Icon className="w-7 h-7 text-primary-600" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600">
                    {feature.description}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Sources Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Источники данных
            </h2>
            <p className="text-lg text-gray-600">
              Мы собираем публикации из ведущих научных баз данных России и мира
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { name: 'eLibrary.ru', desc: 'Российский индекс научного цитирования' },
              { name: 'CyberLeninka', desc: 'Открытая научная библиотека' },
              { name: 'arXiv.org', desc: 'Препринты по физике, математике, CS' },
              { name: 'МГУ', desc: 'Публикации Московского университета' },
              { name: 'СПбГУ', desc: 'Публикации СПбГУ' },
              { name: 'РАН', desc: 'Публикации Академии наук' },
            ].map((source, idx) => (
              <div key={idx} className="bg-white rounded-lg p-4 border border-gray-200 hover:shadow-md transition-shadow">
                <h4 className="font-semibold text-gray-900">{source.name}</h4>
                <p className="text-sm text-gray-500">{source.desc}</p>
              </div>
            ))}
          </div>

          <div className="text-center mt-8">
            <Link
              to="/stats"
              className="inline-flex items-center text-primary-600 hover:text-primary-700 font-medium"
            >
              Посмотреть полную статистику
              <ChevronRight className="w-5 h-5 ml-1" />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-6">
            Готовы начать исследование?
          </h2>
          <p className="text-lg text-gray-600 mb-8">
            Используйте нашу платформу для поиска релевантных научных статей
          </p>
          <Link
            to="/search"
            className="btn-primary text-lg px-8 py-4 inline-flex items-center"
          >
            <Search className="w-5 h-5 mr-2" />
            Перейти к поиску
          </Link>
        </div>
      </section>
    </div>
  )
}
