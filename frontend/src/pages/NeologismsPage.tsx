import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function NeologismsPage() {
    const [searchParams, setSearchParams] = useSearchParams()
    const [results, setResults] = useState<any[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const limit = 100

    const getParam = (key: string) => searchParams.get(key) || ''
    const offset = Number(searchParams.get('offset') || 0)

    const fetchNeologisms = useCallback(async (currentOffset: number = 0) => {
        setLoading(true)
        setError('')
        try {
            const params = new URLSearchParams()
            if (getParam('min_pages')) params.append('min_pages', getParam('min_pages'))
            if (getParam('max_pages')) params.append('max_pages', getParam('max_pages'))
            if (getParam('min_freq')) params.append('min_freq', getParam('min_freq'))
            if (getParam('max_freq')) params.append('max_freq', getParam('max_freq'))
            if (getParam('min_depth')) params.append('min_depth', getParam('min_depth'))
            if (getParam('max_depth')) params.append('max_depth', getParam('max_depth'))
            params.append('offset', currentOffset.toString())
            params.append('limit', limit.toString())

            const response = await fetch(`${API_URL}/neologisms?${params.toString()}`)
            if (!response.ok) throw new Error('Failed to fetch data')
            const data = await response.json()
            setResults(data.results)
            setTotal(data.total)
        } catch (err: any) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [searchParams])

    useEffect(() => {
        fetchNeologisms(offset)
    }, [fetchNeologisms, offset])

    const updateFilter = (key: string, value: string) => {
        const next = new URLSearchParams(searchParams)
        if (value) {
            next.set(key, value)
        } else {
            next.delete(key)
        }
        next.delete('offset')
        setSearchParams(next)
    }

    const handleApply = () => {
        fetchNeologisms(0)
    }

    const handlePrev = () => {
        if (offset > 0) {
            const next = new URLSearchParams(searchParams)
            next.set('offset', String(Math.max(0, offset - limit)))
            setSearchParams(next)
        }
    }

    const handleNext = () => {
        if (offset + limit < total) {
            const next = new URLSearchParams(searchParams)
            next.set('offset', String(offset + limit))
            setSearchParams(next)
        }
    }

    const hasNext = offset + limit < total
    const hasPrev = offset > 0

    return (
        <div className="neologisms-page">
            <div className="neologisms-header-bar">
                <Link to="/" className="back-link">&larr; Back to Review</Link>
                <h2>Neologisms</h2>
                <span className="result-count">({total} results)</span>
            </div>

            <div className="neologisms-filters">
                <div className="filter-group">
                    <label>Min Pages: </label>
                    <input type="number" min={0} value={getParam('min_pages')} onChange={e => updateFilter('min_pages', e.target.value)} />
                </div>
                <div className="filter-group">
                    <label>Max Pages: </label>
                    <input type="number" min={0} value={getParam('max_pages')} onChange={e => updateFilter('max_pages', e.target.value)} />
                </div>
                <div className="filter-group">
                    <label>Min Freq: </label>
                    <input type="number" min={0} value={getParam('min_freq')} onChange={e => updateFilter('min_freq', e.target.value)} />
                </div>
                <div className="filter-group">
                    <label>Max Freq: </label>
                    <input type="number" min={0} value={getParam('max_freq')} onChange={e => updateFilter('max_freq', e.target.value)} />
                </div>
                <div className="filter-group">
                    <label>Min Depth: </label>
                    <input type="number" min={0} value={getParam('min_depth')} onChange={e => updateFilter('min_depth', e.target.value)} />
                </div>
                <div className="filter-group">
                    <label>Max Depth: </label>
                    <input type="number" min={0} value={getParam('max_depth')} onChange={e => updateFilter('max_depth', e.target.value)} />
                </div>
                <button onClick={handleApply} disabled={loading} className="apply-btn">
                    {loading ? 'Applying...' : 'Apply Filters'}
                </button>
            </div>

            {error && <p className="error">⚠️ {error}</p>}

            <table className="neologisms-table">
                <thead>
                    <tr>
                        <th>Word</th>
                        <th>Total Freq</th>
                        <th># Pages</th>
                        <th>Depth</th>
                    </tr>
                </thead>
                <tbody>
                    {results.map((item, i) => (
                        <tr key={i}>
                            <td>{item.word}</td>
                            <td>{item.total_freq}</td>
                            <td>{item.n_pages}</td>
                            <td>{item.min_depth ?? '—'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {results.length === 0 && !loading && (
                <p className="no-results">No results found.</p>
            )}

            <div className="neologisms-pagination">
                <button onClick={handlePrev} disabled={!hasPrev || loading}>&laquo; Prev</button>
                <span>Showing {total === 0 ? 0 : offset + 1} - {Math.min(offset + limit, total)} of {total}</span>
                <button onClick={handleNext} disabled={!hasNext || loading}>Next &raquo;</button>
            </div>
        </div>
    )
}
