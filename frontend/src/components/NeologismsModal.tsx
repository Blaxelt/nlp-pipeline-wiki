import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface NeologismsModalProps {
    show: boolean;
    onClose: () => void;
}

export function NeologismsModal({ show, onClose }: NeologismsModalProps) {
    const [minPages, setMinPages] = useState('')
    const [maxPages, setMaxPages] = useState('')
    const [minFreq, setMinFreq] = useState('')
    const [maxFreq, setMaxFreq] = useState('')
    const [minDepth, setMinDepth] = useState('')
    const [maxDepth, setMaxDepth] = useState('')
    const [offset, setOffset] = useState(0)
    const limit = 100
    const [results, setResults] = useState<any[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const fetchNeologisms = async (currentOffset: number = 0) => {
        setLoading(true)
        setError('')
        try {
            const params = new URLSearchParams()
            if (minPages) params.append('min_pages', minPages)
            if (maxPages) params.append('max_pages', maxPages)
            if (minFreq) params.append('min_freq', minFreq)
            if (maxFreq) params.append('max_freq', maxFreq)
            if (minDepth) params.append('min_depth', minDepth)
            if (maxDepth) params.append('max_depth', maxDepth)
            params.append('offset', currentOffset.toString())
            params.append('limit', limit.toString())

            const response = await fetch(`${API_URL}/neologisms?${params.toString()}`)
            if (!response.ok) throw new Error('Failed to fetch data')
            const data = await response.json()
            setResults(data.results)
            setTotal(data.total)
            setOffset(currentOffset)
        } catch (err: any) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (show) {
            fetchNeologisms(0)
        }
    }, [show])

    const handleApply = () => {
        fetchNeologisms(0)
    }

    const handlePrev = () => {
        if (offset > 0) {
            fetchNeologisms(Math.max(0, offset - limit))
        }
    }

    const handleNext = () => {
        if (offset + limit < total) {
            fetchNeologisms(offset + limit)
        }
    }

    const handleMinPages = (val: string) => {
        setMinPages(val)
        if (maxPages && Number(val) > Number(maxPages)) setMaxPages(val)
    }

    const handleMaxPages = (val: string) => {
        setMaxPages(val)
        if (minPages && Number(val) < Number(minPages)) setMinPages(val)
    }

    const handleMinFreq = (val: string) => {
        setMinFreq(val)
        if (maxFreq && Number(val) > Number(maxFreq)) setMaxFreq(val)
    }

    const handleMaxFreq = (val: string) => {
        setMaxFreq(val)
        if (minFreq && Number(val) < Number(minFreq)) setMinFreq(val)
    }

    const handleMinDepth = (val: string) => {
        setMinDepth(val)
        if (maxDepth && Number(val) > Number(maxDepth)) setMaxDepth(val)
    }

    const handleMaxDepth = (val: string) => {
        setMaxDepth(val)
        if (minDepth && Number(val) < Number(minDepth)) setMinDepth(val)
    }

    if (!show) return null

    const hasNext = offset + limit < total
    const hasPrev = offset > 0

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal neologisms-modal" onClick={(e) => e.stopPropagation()}>
                <div className="neologisms-header">
                    <h3>Neologisms Filter ({total} results)</h3>
                    <button onClick={onClose}>Close</button>
                </div>

                <div className="neologisms-filters">
                    <div className="filter-group">
                        <label>Min Pages: </label>
                        <input type="number" min={0} value={minPages} onChange={e => handleMinPages(e.target.value)} />
                    </div>
                    <div className="filter-group">
                        <label>Max Pages: </label>
                        <input type="number" min={0} value={maxPages} onChange={e => handleMaxPages(e.target.value)} />
                    </div>
                    <div className="filter-group">
                        <label>Min Freq: </label>
                        <input type="number" min={0} value={minFreq} onChange={e => handleMinFreq(e.target.value)} />
                    </div>
                    <div className="filter-group">
                        <label>Max Freq: </label>
                        <input type="number" min={0} value={maxFreq} onChange={e => handleMaxFreq(e.target.value)} />
                    </div>
                    <div className="filter-group">
                        <label>Min Depth: </label>
                        <input type="number" min={0} value={minDepth} onChange={e => handleMinDepth(e.target.value)} />
                    </div>
                    <div className="filter-group">
                        <label>Max Depth: </label>
                        <input type="number" min={0} value={maxDepth} onChange={e => handleMaxDepth(e.target.value)} />
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
        </div>
    )
}
