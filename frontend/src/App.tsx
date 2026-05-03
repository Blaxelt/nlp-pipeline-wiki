import './App.css'
import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { TopBar } from './components/TopBar'
import { LoadDumpModal } from './components/LoadDumpModal'
import { ArticlePanels } from './components/ArticlePanels'
import { CleanerDiff } from './components/CleanerDiff'
import { NeologismsPage } from './pages/NeologismsPage'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [articleId, setArticleId] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [articleText, setArticleText] = useState('')
  const [showPicker, setShowPicker] = useState(false)
  const [date, setDate] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [modalError, setModalError] = useState('')
  const [iframeSrc, setIframeSrc] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [extractMsg, setExtractMsg] = useState('')
  const [entities, setEntities] = useState<any[]>([])
  const [cleanerResults, setCleanerResults] = useState<any>(null)
  const [cleanerLoading, setCleanerLoading] = useState(false)
  const [showDiff, setShowDiff] = useState(false)

  const buildIframeSrc = (id: string, fragment?: string) => {
    const base = `https://es.wikipedia.org/w/index.php?oldid=${id}`
    if (fragment) {
      return `${base}#:~:text=${encodeURIComponent(fragment)}`
    }
    return base
  }

  const loadArticle = (id: string) => {
    setError('')
    setArticleId(id)
    setInputValue(id)
    setIframeSrc(buildIframeSrc(id))
    setEntities([])
    fetch(`${API_URL}/articles/${id}`)
      .then(response => {
        if (!response.ok) throw new Error('Article not found')
        return response.json()
      })
      .then(data => setArticleText(data.text))
      .catch(error => setError(error.message))
  }

  const handleSearch = () => {
    if (!inputValue.trim()) {
      setError('Enter a revision ID')
      return
    }
    if (isNaN(Number(inputValue))) {
      setError('ID must be a number')
      return
    }
    loadArticle(inputValue)
  }

  const handleAdjacent = (direction: 'next' | 'prev') => {
    fetch(`${API_URL}/articles/${articleId}/${direction}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(direction === 'next' ? 'No next article' : 'No prev article')
        }
        return response.json()
      })
      .then(data => loadArticle(data.id))
      .catch(error => setError(error.message))
  }

  const handleSubmit = async () => {
    if (!date) return
    setLoading(true)
    setModalError('')
    try {
      const response = await fetch(`${API_URL}/articles/load?date=${date.replace(/-/g, '')}`, {
        method: 'POST',
      })
      if (!response.ok) {
        const data = await response.json()
        setModalError(data.detail || 'Unknown error')
        return
      }
      const data = await response.json()
      console.log('Respuesta:', data)
      setShowPicker(false)
    } catch (err) {
      setModalError('Could not reach the server.')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleTextSelection = () => {
    if (!articleId) return

    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) return

    const selectedText = selection.toString().trim()
    if (!selectedText || selectedText.length < 3) return

    const fragment = selectedText.split(/\s+/).slice(0, 15).join(' ')

    setIframeSrc(buildIframeSrc(articleId, fragment))
  }

  const handleCompareCleaners = async () => {
    if (!articleId) return
    setCleanerLoading(true)
    setShowDiff(true)
    try {
      const response = await fetch(`${API_URL}/articles/${articleId}/compare-cleaners`)
      if (!response.ok) throw new Error('Error')
      const data = await response.json()
      setCleanerResults(data)
    } catch {
      setCleanerResults(null)
    } finally {
      setCleanerLoading(false)
    }
  }

  const handleExtractEntities = async () => {
    if (!articleId || extracting) return
    setExtracting(true)
    setExtractMsg('')
    try {
      const response = await fetch(`${API_URL}/articles/${articleId}/extract-entities`, {
        method: 'POST',
      })
      if (!response.ok) {
        const data = await response.json()
        setExtractMsg(`❌ ${data.detail || 'Error'}`)
        return
      }
      const data = await response.json()
      setEntities(data.entities || [])
      setExtractMsg(`✅ ${data.count} entities saved`)
    } catch {
      setExtractMsg('❌ Could not reach server')
    } finally {
      setExtracting(false)
      setTimeout(() => setExtractMsg(''), 4000)
    }
  }

  return (
    <Routes>
      <Route path="/" element={
        <div>
          <TopBar
            articleId={articleId}
            inputValue={inputValue}
            setInputValue={setInputValue}
            handleSearch={handleSearch}
            handleAdjacent={handleAdjacent}
            setShowPicker={setShowPicker}
            handleExtractEntities={handleExtractEntities}
            extracting={extracting}
            extractMsg={extractMsg}
            error={error}
            handleCompareCleaners={handleCompareCleaners}
            articleId_forCompare={articleId}
          />

          <LoadDumpModal
            showPicker={showPicker}
            setShowPicker={setShowPicker}
            date={date}
            setDate={setDate}
            handleSubmit={handleSubmit}
            loading={loading}
            modalError={modalError}
          />

          {showDiff && (
            <CleanerDiff
              results={cleanerResults}
              loading={cleanerLoading}
              onClose={() => { setShowDiff(false); setCleanerResults(null) }}
            />
          )}

          <ArticlePanels
            articleText={articleText}
            iframeSrc={iframeSrc}
            handleTextSelection={handleTextSelection}
            entities={entities}
          />
        </div>
      } />
      <Route path="/neologisms" element={<NeologismsPage />} />
    </Routes>
  )
}

export default App
