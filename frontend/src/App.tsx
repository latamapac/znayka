import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import PaperDetailPage from './pages/PaperDetailPage'
import AboutPage from './pages/AboutPage'
import StatsPage from './pages/StatsPage'
import MonitorPage from './pages/MonitorPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/paper/:id" element={<PaperDetailPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/stats" element={<StatsPage />} />
        <Route path="/monitor" element={<MonitorPage />} />
      </Routes>
    </Layout>
  )
}

export default App
