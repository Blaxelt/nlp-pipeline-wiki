import { useState, useEffect } from 'react'
import { TopBar } from '../components/TopBar'
import { LoadDumpModal } from '../components/LoadDumpModal'
import { DumpSelectModal } from '../components/DumpSelectModal'
import { ArticlePanels, type Entity } from '../components/ArticlePanels'
import { CleanerDiff, type CleanerResults } from '../components/CleanerDiff'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function buildIframeSrc(id: string, fragment?: string) {
  const base = `https://es.wikipedia.org/w/index.php?oldid=${id}`
  if (fragment) {
    return `${base}#:~:text=${encodeURIComponent(fragment)}`
  }
  return base
}

type Phase = 'starting' | 'selecting' | 'ready'

export function HomePage() {
  const [phase, setPhase] = useState<Phase>('starting')
  const [currentDump, setCurrentDump] = useState<string | null>(null)
  const [articleId, setArticleId] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [articleText, setArticleText] = useState('')
  const [showPicker, setShowPicker] = useState(false)
  const [error, setError] = useState('')
  const [iframeSrc, setIframeSrc] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [extractMsg, setExtractMsg] = useState('')
  const [entities, setEntities] = useState<Entity[]>([])
  const [cleanerResults, setCleanerResults] = useState<CleanerResults | null>(null)
  const [cleanerLoading, setCleanerLoading] = useState(false)
  const [showDiff, setShowDiff] = useState(false)

  useEffect(() => {
    if (phase !== 'starting') return
    const poll = setInterval(() => {
      fetch(`${API_URL}/articles/available-dumps`)
        .then(res => {
          if (!res.ok) return
          clearInterval(poll)
          return res.json()
        })
        .then(data => {
          if (!data) return
          if (data.current) {
            setCurrentDump(data.current)
            setPhase('ready')
          } else {
            setPhase('selecting')
          }
        })
        .catch(() => {})
    }, 1000)
    return () => clearInterval(poll)
  }, [phase])

  const handleSelectDump = (date: string) => {
    setCurrentDump(date)
    setPhase('ready')
  }

  const handleCloseDumpModal = () => {
    setPhase('ready')
  }

  const loadArticle = (id: string, text?: string) => {
    setError('')
    setArticleId(id)
    setInputValue(id)
    setIframeSrc(buildIframeSrc(id))
    setEntities([])
    if (text !== undefined) {
      setArticleText(text)
      return
    }
    fetch(`${API_URL}/articles/${id}`)
      .then(response => {
        if (!response.ok) throw new Error('Article not found')
        return response.json()
      })
      .then(data => setArticleText(data.text))
      .catch(error => setError(error.message))
  }

  const handleSearch = async () => {
    if (!inputValue.trim()) {
      setError('Enter a revision ID')
      return
    }
    setError('')

    const trimmed = inputValue.trim()
    if (isNaN(Number(trimmed))) {
      setError('Revision ID must be a number')
      return
    }

    loadArticle(trimmed)
  }

  const handleLoadByTitle = async (title: string) => {
    setError('')
    setEntities([])
    try {
      const res = await fetch(`${API_URL}/articles/by-title/${encodeURIComponent(title)}`)
      if (!res.ok) throw new Error('Article not found')
      const data = await res.json()
      loadArticle(data.revision_id, data.text)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
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

  const handleDumpLoaded = (date: string) => {
    setCurrentDump(date)
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

  if (phase === 'starting') {
    return (
      <div className="flex items-center justify-center h-screen text-[#888] text-lg">
        Setting up...
      </div>
    )
  }

  if (phase === 'selecting') {
    return <DumpSelectModal onLoad={handleSelectDump} onClose={handleCloseDumpModal} currentDump={currentDump} />
  }

  return (
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
        onSelectTitle={handleLoadByTitle}
        currentDump={currentDump}
      />

      {!currentDump && (
        <div className="bg-[#2a1a1a] border border-[#5a3a3a] text-[#e0a0a0] px-4 py-2 m-2.5 rounded text-sm">
          No dump loaded - article search is disabled. Use <strong>Load bz2</strong> to fetch a dump.
        </div>
      )}

      <LoadDumpModal
        showPicker={showPicker}
        setShowPicker={setShowPicker}
        onSuccess={handleDumpLoaded}
      />

      {showDiff ? (
        <CleanerDiff
          results={cleanerResults}
          loading={cleanerLoading}
          onClose={() => { setShowDiff(false); setCleanerResults(null) }}
        />
      ) : null}

      <ArticlePanels
        articleText={articleText}
        iframeSrc={iframeSrc}
        handleTextSelection={handleTextSelection}
        entities={entities}
      />
    </div>
  )
}
