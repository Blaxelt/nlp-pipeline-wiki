import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, Link } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Review {
    status: 'valid' | 'discarded'
    reason: string
    updated_at: string
}

interface PageInfo {
    freq: number
    categories: string[] | null
    min_depth: number | null
}

interface NeologismItem {
    word: string
    total_freq: number
    n_pages: number
    min_depth: number | null
    pages: Record<string, PageInfo>
    review: Review | null
}

export function NeologismsPage() {
    const [searchParams, setSearchParams] = useSearchParams()
    const [results, setResults] = useState<NeologismItem[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [selectedItem, setSelectedItem] = useState<NeologismItem | null>(null)
    const [detailOffset, setDetailOffset] = useState(0)
    const [reviewReason, setReviewReason] = useState('')
    const [savingReview, setSavingReview] = useState(false)
    const limit = 100
    const detailLimit = 50

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
            if (getParam('review_status')) params.append('review_status', getParam('review_status'))
            params.append('offset', currentOffset.toString())
            params.append('limit', limit.toString())

            const response = await fetch(`${API_URL}/neologisms?${params.toString()}`)
            if (!response.ok) throw new Error('Failed to fetch data')
            const data = await response.json()
            setResults(data.results as NeologismItem[])
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

    const openDetail = (item: NeologismItem) => {
        setSelectedItem(item)
        setDetailOffset(0)
        setReviewReason(item.review?.reason || '')
    }

    const closeDetail = () => {
        setSelectedItem(null)
        setDetailOffset(0)
        setReviewReason('')
    }

    const detailPages = selectedItem ? Object.entries(selectedItem.pages) : []
    const detailTotal = detailPages.length
    const detailHasNext = detailOffset + detailLimit < detailTotal
    const detailHasPrev = detailOffset > 0
    const detailSlice = detailPages.slice(detailOffset, detailOffset + detailLimit)

    const wikiUrl = (title: string) =>
        `https://es.wikipedia.org/wiki/${encodeURIComponent(title.replace(/ /g, '_'))}`

    const categoryUrl = (cat: string) =>
        `https://es.wikipedia.org/wiki/Categoría:${encodeURIComponent(cat.replace(/ /g, '_'))}`

    const saveReview = async (status: 'valid' | 'discarded') => {
        if (!selectedItem) return
        setSavingReview(true)
        try {
            const response = await fetch(`${API_URL}/neologisms/review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    word: selectedItem.word,
                    status,
                    reason: reviewReason,
                }),
            })
            if (!response.ok) throw new Error('Failed to save review')
            const data = await response.json()
            const newReview: Review = data.review

            // Update selected item
            setSelectedItem({ ...selectedItem, review: newReview })

            // Update results list in place
            setResults(prev =>
                prev.map(item =>
                    item.word === selectedItem.word
                        ? { ...item, review: newReview }
                        : item
                )
            )
        } catch (err: any) {
            setError(err.message)
        } finally {
            setSavingReview(false)
        }
    }

    const statusBadge = (review: Review | null) => {
        if (!review) return <span className="badge unreviewed">—</span>
        if (review.status === 'valid') return <span className="badge valid">Valid</span>
        return <span className="badge discarded">Discarded</span>
    }

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
                <div className="filter-group">
                    <label>Status: </label>
                    <select value={getParam('review_status')} onChange={e => updateFilter('review_status', e.target.value)}>
                        <option value="">All</option>
                        <option value="valid">Valid</option>
                        <option value="discarded">Discarded</option>
                        <option value="unreviewed">Unreviewed</option>
                    </select>
                </div>
            </div>

            {error && <p className="error">⚠️ {error}</p>}

            <table className="neologisms-table">
                <thead>
                    <tr>
                        <th>Word</th>
                        <th>Total Freq</th>
                        <th># Pages</th>
                        <th>Depth</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {results.map((item, i) => (
                        <tr key={i} onClick={() => openDetail(item)} className="clickable-row">
                            <td>{item.word}</td>
                            <td>{item.total_freq}</td>
                            <td>{item.n_pages}</td>
                            <td>{item.min_depth ?? '—'}</td>
                            <td>{statusBadge(item.review)}</td>
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

            {selectedItem && (
                <div className="modal-overlay" onClick={closeDetail}>
                    <div className="modal neologism-detail-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="detail-header">
                            <h3>{selectedItem.word}</h3>
                            <button onClick={closeDetail}>Close</button>
                        </div>

                        <div className="review-actions">
                            {statusBadge(selectedItem.review)}
                            <div className="review-buttons">
                                <button
                                    className={`review-btn valid-btn ${selectedItem.review?.status === 'valid' ? 'active' : ''}`}
                                    onClick={() => saveReview('valid')}
                                    disabled={savingReview}
                                >
                                    {savingReview ? 'Saving…' : 'Mark Valid'}
                                </button>
                                <button
                                    className={`review-btn discard-btn ${selectedItem.review?.status === 'discarded' ? 'active' : ''}`}
                                    onClick={() => saveReview('discarded')}
                                    disabled={savingReview}
                                >
                                    {savingReview ? 'Saving…' : 'Discard'}
                                </button>
                            </div>
                        </div>

                        <div className="review-reason">
                            <label>Reason / Comment:</label>
                            <textarea
                                rows={2}
                                value={reviewReason}
                                onChange={e => setReviewReason(e.target.value)}
                                placeholder="Optional reason for the review…"
                            />
                        </div>

                        <p className="detail-meta">
                            {selectedItem.total_freq} occurrences across {selectedItem.n_pages} pages
                        </p>
                        <table className="neologisms-table detail-table">
                            <thead>
                                <tr>
                                    <th>Page</th>
                                    <th>Freq</th>
                                    <th>Depth</th>
                                    <th>Categories</th>
                                </tr>
                            </thead>
                            <tbody>
                                {detailSlice.map(([title, info]) => (
                                    <tr key={title}>
                                        <td>
                                            <a href={wikiUrl(title)} target="_blank" rel="noopener noreferrer">
                                                {title}
                                            </a>
                                        </td>
                                        <td>{info.freq}</td>
                                        <td>{info.min_depth ?? '—'}</td>
                                        <td>
                                            {info.categories ? (
                                                info.categories.map((cat, idx) => (
                                                    <span key={cat}>
                                                        <a href={categoryUrl(cat)} target="_blank" rel="noopener noreferrer">
                                                            {cat}
                                                        </a>
                                                        {idx < info.categories!.length - 1 && ', '}
                                                    </span>
                                                ))
                                            ) : '—'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {detailTotal > detailLimit && (
                            <div className="neologisms-pagination detail-pagination">
                                <button onClick={() => setDetailOffset(Math.max(0, detailOffset - detailLimit))} disabled={!detailHasPrev}>&laquo; Prev</button>
                                <span>{detailOffset + 1} - {Math.min(detailOffset + detailLimit, detailTotal)} of {detailTotal}</span>
                                <button onClick={() => setDetailOffset(detailOffset + detailLimit)} disabled={!detailHasNext}>Next &raquo;</button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
