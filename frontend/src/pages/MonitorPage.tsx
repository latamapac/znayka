import { useEffect, useState, useRef } from 'react'
import { 
  Activity, 
  FileText, 
  Clock, 
  Database,
  TrendingUp,
  Loader2,
  Zap,
  RefreshCw
} from 'lucide-react'

interface LiveStats {
  total_papers: number
  papers_today: number
  papers_this_hour: number
  active_crawls: number
  completed_crawls: number
  recent_papers_count: number
  last_updated: string
}

interface RecentPaper {
  id: string
  title: string
  source: string
  authors: string[]
  year: number
  added_at: string
  has_pdf: boolean
}

interface CrawlRecord {
  timestamp: string
  source: string
  query: string
  papers_found: number
  papers_new: number
}

export default function MonitorPage() {
  const [liveStats, setLiveStats] = useState<LiveStats | null>(null)
  const [recentPapers, setRecentPapers] = useState<RecentPaper[]>([])
  const [crawlHistory, setCrawlHistory] = useState<CrawlRecord[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch initial data
  const fetchData = async () => {
    try {
      const [statsRes, papersRes, historyRes] = await Promise.all([
        fetch('/api/v1/monitor/live'),
        fetch('/api/v1/monitor/recent-papers'),
        fetch('/api/v1/monitor/crawl-history')
      ])

      if (statsRes.ok) {
        const data = await statsRes.json()
        setLiveStats(data.live_stats)
      }
      if (papersRes.ok) {
        const data = await papersRes.json()
        setRecentPapers(data.papers)
      }
      if (historyRes.ok) {
        const data = await historyRes.json()
        setCrawlHistory(data.history)
      }
      setLastUpdate(new Date())
    } catch (error) {
      console.error('Error fetching data:', error)
    }
  }

  // Setup SSE connection
  const connectSSE = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const es = new EventSource('/api/v1/monitor/sse')
    
    es.onopen = () => {
      setIsConnected(true)
      console.log('Monitor connected')
    }

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'new_paper') {
          setRecentPapers(prev => [data.data, ...prev].slice(0, 50))
          setLiveStats(prev => prev ? {
            ...prev,
            total_papers: prev.total_papers + 1,
            papers_today: prev.papers_today + 1,
            papers_this_hour: prev.papers_this_hour + 1
          } : null)
        }
        
        if (data.type === 'crawl_update') {
          setLiveStats(prev => prev ? {
            ...prev,
            active_crawls: data.data.running,
            completed_crawls: data.data.completed
          } : null)
        }
        
        if (data.type === 'initial') {
          setLiveStats(data.data)
        }
        
        setLastUpdate(new Date())
      } catch (error) {
        console.error('Error parsing SSE data:', error)
      }
    }

    es.onerror = () => {
      setIsConnected(false)
      es.close()
      
      // Reconnect after 5 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connectSSE()
      }, 5000)
    }

    eventSourceRef.current = es
  }

  useEffect(() => {
    fetchData()
    connectSSE()

    // Periodic refresh as backup
    const interval = setInterval(fetchData, 30000)

    return () => {
      clearInterval(interval)
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  const formatTime = (isoString: string) => {
    return new Date(isoString).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatRelativeTime = (isoString: string) => {
    const date = new Date(isoString)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (diff < 60) return `${diff} сек назад`
    if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`
    if (diff < 86400) return `${Math.floor(diff / 3600)} час назад`
    return `${Math.floor(diff / 86400)} дн назад`
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Activity className="w-8 h-8 text-primary-600" />
            Live Monitor
          </h1>
          <p className="text-gray-600 mt-2">
            Real-time database activity and crawler status
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${
            isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            {isConnected ? 'Live' : 'Reconnecting...'}
          </div>
          <button 
            onClick={fetchData}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Live Stats Grid */}
      {liveStats && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="card bg-gradient-to-br from-primary-50 to-white border-primary-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">Всего статей</p>
                <p className="text-3xl font-bold text-gray-900">
                  {liveStats.total_papers.toLocaleString()}
                </p>
              </div>
              <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
                <Database className="w-6 h-6 text-primary-600" />
              </div>
            </div>
          </div>

          <div className="card bg-gradient-to-br from-green-50 to-white border-green-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">Сегодня добавлено</p>
                <p className="text-3xl font-bold text-gray-900">
                  {liveStats.papers_today.toLocaleString()}
                </p>
                <p className="text-xs text-green-600 mt-1">
                  +{liveStats.papers_this_hour} за час
                </p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>

          <div className="card bg-gradient-to-br from-blue-50 to-white border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">Активные краулеры</p>
                <p className="text-3xl font-bold text-gray-900">
                  {liveStats.active_crawls}
                </p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <Loader2 className={`w-6 h-6 text-blue-600 ${liveStats.active_crawls > 0 ? 'animate-spin' : ''}`} />
              </div>
            </div>
          </div>

          <div className="card bg-gradient-to-br from-purple-50 to-white border-purple-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">Завершено</p>
                <p className="text-3xl font-bold text-gray-900">
                  {liveStats.completed_crawls.toLocaleString()}
                </p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                <Zap className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Recent Papers Feed */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary-600" />
              Последние добавленные
            </h2>
            <span className="text-sm text-gray-500">
              {recentPapers.length} papers
            </span>
          </div>

          <div className="space-y-4 max-h-[600px] overflow-y-auto">
            {recentPapers.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Нет данных</p>
            ) : (
              recentPapers.map((paper, idx) => (
                <div 
                  key={paper.id} 
                  className={`p-4 rounded-lg border transition-all hover:shadow-md ${
                    idx === 0 ? 'bg-green-50 border-green-200 animate-pulse' : 'bg-gray-50 border-gray-100'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 line-clamp-2">
                        {paper.title}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {paper.authors.join(', ')}
                      </p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                        <span className="capitalize">{paper.source}</span>
                        <span>•</span>
                        <span>{paper.year}</span>
                        {paper.has_pdf && (
                          <>
                            <span>•</span>
                            <span className="text-green-600">PDF</span>
                          </>
                        )}
                      </div>
                    </div>
                    <span className="text-xs text-gray-400 whitespace-nowrap">
                      {formatRelativeTime(paper.added_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Crawl History */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary-600" />
              История краулинга
            </h2>
            <span className="text-sm text-gray-500">
              {crawlHistory.length} records
            </span>
          </div>

          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {crawlHistory.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Нет данных</p>
            ) : (
              crawlHistory.map((record, idx) => (
                <div 
                  key={idx}
                  className="p-4 bg-gray-50 rounded-lg border border-gray-100"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">
                        {record.query}
                      </p>
                      <p className="text-sm text-gray-500 capitalize">
                        {record.source}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-primary-600">
                        +{record.papers_new}
                      </p>
                      <p className="text-xs text-gray-400">
                        {formatTime(record.timestamp)}
                      </p>
                    </div>
                  </div>
                  {record.papers_found > record.papers_new && (
                    <p className="text-xs text-gray-400 mt-2">
                      Найдено: {record.papers_found} | Новых: {record.papers_new}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Last Update Footer */}
      <div className="mt-8 text-center text-sm text-gray-500">
        Последнее обновление: {lastUpdate.toLocaleTimeString('ru-RU')}
      </div>
    </div>
  )
}
