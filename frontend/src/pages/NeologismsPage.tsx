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
    mean_depth: number | null
}

interface NeologismItem {
    word: string
    total_freq: number
    n_pages: number
    mean_depth: number | null
    num_categories: number
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
        if (!review) return <span className="inline-block px-2 py-0.5 rounded-full text-[0.8rem] font-medium text-[#888]">—</span>
        if (review.status === 'valid') return <span className="inline-block px-2 py-0.5 rounded-full text-[0.8rem] font-medium bg-[rgba(40,167,69,0.2)] text-[#7ce87c]">Valid</span>
        return <span className="inline-block px-2 py-0.5 rounded-full text-[0.8rem] font-medium bg-[rgba(220,53,69,0.2)] text-[#f28b8b]">Discarded</span>
    }

    return (
        <div className="p-6 text-[#e0e0e0]">
            <div className="flex items-center gap-4 mb-4">
                <Link to="/" className="px-2.5 py-0.75 bg-[#333] text-[#e0e0e0] border border-[#555] rounded text-[0.9rem] no-underline cursor-pointer hover:bg-[#444]">&larr; Back to Review</Link>
                <h2 className="m-0">Neologisms</h2>
                <span className="text-[#888] text-[0.9rem]">({total} results)</span>
            </div>

            <div className="flex gap-3 my-6 flex-wrap items-end">
                <div className="flex flex-col">
                    <label className="text-[0.85rem] mb-1">Min Pages: </label>
                    <input type="number" min={0} value={getParam('min_pages')} onChange={e => updateFilter('min_pages', e.target.value)} className="w-20 p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0]" />
                </div>
                <div className="flex flex-col">
                    <label className="text-[0.85rem] mb-1">Max Pages: </label>
                    <input type="number" min={0} value={getParam('max_pages')} onChange={e => updateFilter('max_pages', e.target.value)} className="w-20 p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0]" />
                </div>
                <div className="flex flex-col">
                    <label className="text-[0.85rem] mb-1">Min Freq: </label>
                    <input type="number" min={0} value={getParam('min_freq')} onChange={e => updateFilter('min_freq', e.target.value)} className="w-20 p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0]" />
                </div>
                <div className="flex flex-col">
                    <label className="text-[0.85rem] mb-1">Max Freq: </label>
                    <input type="number" min={0} value={getParam('max_freq')} onChange={e => updateFilter('max_freq', e.target.value)} className="w-20 p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0]" />
                </div>
                <div className="flex flex-col">
                    <label className="text-[0.85rem] mb-1">Min Depth: </label>
                    <input type="number" min={0} value={getParam('min_depth')} onChange={e => updateFilter('min_depth', e.target.value)} className="w-20 p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0]" />
                </div>
                <div className="flex flex-col">
                    <label className="text-[0.85rem] mb-1">Max Depth: </label>
                    <input type="number" min={0} value={getParam('max_depth')} onChange={e => updateFilter('max_depth', e.target.value)} className="w-20 p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0]" />
                </div>
                <div className="flex flex-col">
                    <label className="text-[0.85rem] mb-1">Status: </label>
                    <select value={getParam('review_status')} onChange={e => updateFilter('review_status', e.target.value)} className="w-30 p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0]">
                        <option value="">All</option>
                        <option value="valid">Valid</option>
                        <option value="discarded">Discarded</option>
                        <option value="unreviewed">Unreviewed</option>
                    </select>
                </div>
            </div>

            {error && <p className="text-red-500">⚠️ {error}</p>}

            <table className="w-full border-collapse text-left mb-4 table-fixed [&_th:nth-child(1)]:w-[30%] [&_th:nth-child(2)]:w-[12%] [&_th:nth-child(3)]:w-[12%] [&_th:nth-child(4)]:w-[12%] [&_th:nth-child(5)]:w-[14%] [&_th:nth-child(6)]:w-[20%]">
                <thead>
                    <tr>
                        <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]">Word</th>
                        <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]">Total Freq</th>
                        <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]"># Pages</th>
                        <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]">Depth</th>
                        <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]"># Cats</th>
                        <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {results.map((item, i) => (
                        <tr key={i} onClick={() => openDetail(item)} className="cursor-pointer hover:bg-[#333]">
                            <td className="p-2 border-b border-[#444] wrap-break-word">{item.word}</td>
                            <td className="p-2 border-b border-[#444] wrap-break-word">{item.total_freq}</td>
                            <td className="p-2 border-b border-[#444] wrap-break-word">{item.n_pages}</td>
                            <td className="p-2 border-b border-[#444] wrap-break-word">{item.mean_depth ?? '—'}</td>
                            <td className="p-2 border-b border-[#444] wrap-break-word">{item.num_categories}</td>
                            <td className="p-2 border-b border-[#444] wrap-break-word">{statusBadge(item.review)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {results.length === 0 && !loading && (
                <p className="text-center text-[#888] mt-4">No results found.</p>
            )}

            <div className="flex justify-between items-center mt-4 pt-4 border-t border-[#444]">
                <button onClick={handlePrev} disabled={!hasPrev || loading} className="px-3 py-1.5 bg-[#333] text-[#e0e0e0] border border-[#555] rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">&laquo; Prev</button>
                <span>Showing {total === 0 ? 0 : offset + 1} - {Math.min(offset + limit, total)} of {total}</span>
                <button onClick={handleNext} disabled={!hasNext || loading} className="px-3 py-1.5 bg-[#333] text-[#e0e0e0] border border-[#555] rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">Next &raquo;</button>
            </div>

            {selectedItem && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-100" onClick={closeDetail}>
                    <div className="bg-[rgb(36,34,34)] rounded-xl px-8 py-6 flex flex-col gap-4 min-w-75 shadow-[0_8px_32px_rgba(0,0,0,0.2)] w-[85vw] max-h-[85vh] overflow-y-auto text-[#e0e0e0]" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-between items-center">
                            <h3 className="m-0">{selectedItem.word}</h3>
                            <button onClick={closeDetail} className="bg-[#333] text-[#e0e0e0] border border-[#555] px-3 py-1.5 rounded cursor-pointer">Close</button>
                        </div>

                        <div className="flex items-center gap-4 flex-wrap">
                            {statusBadge(selectedItem.review)}
                            <div className="flex gap-2">
                                <button
                                    className={`px-3.5 py-1.5 rounded border border-[#555] bg-[#2a2a2a] text-[#e0e0e0] cursor-pointer hover:enabled:bg-[#333] ${selectedItem.review?.status === 'valid' ? 'bg-[rgba(40,167,69,0.3)] border-[#28a745] text-[#7ce87c]' : ''}`}
                                    onClick={() => saveReview('valid')}
                                    disabled={savingReview}
                                >
                                    {savingReview ? 'Saving…' : 'Mark Valid'}
                                </button>
                                <button
                                    className={`px-3.5 py-1.5 rounded border border-[#555] bg-[#2a2a2a] text-[#e0e0e0] cursor-pointer hover:enabled:bg-[#333] ${selectedItem.review?.status === 'discarded' ? 'bg-[rgba(220,53,69,0.3)] border-[#dc3545] text-[#f28b8b]' : ''}`}
                                    onClick={() => saveReview('discarded')}
                                    disabled={savingReview}
                                >
                                    {savingReview ? 'Saving…' : 'Discard'}
                                </button>
                            </div>
                        </div>

                        <div className="flex flex-col gap-1">
                            <label className="text-[0.85rem] text-[#aaa]">Reason / Comment:</label>
                            <textarea
                                rows={2}
                                value={reviewReason}
                                onChange={e => setReviewReason(e.target.value)}
                                placeholder="Optional reason for the review…"
                                className="p-2 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0] font-sans resize-y"
                            />
                        </div>

                        <p className="text-[#888] m-0">
                            {selectedItem.total_freq} occurrences across {selectedItem.n_pages} pages
                        </p>
                        <table className="w-full border-collapse text-left mb-4 table-fixed [&_th:nth-child(1)]:w-[25%] [&_th:nth-child(2)]:w-[8%] [&_th:nth-child(3)]:w-[8%] [&_th:nth-child(4)]:w-[59%]">
                            <thead>
                                <tr>
                                    <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]">Page</th>
                                    <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]">Freq</th>
                                    <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]">Depth</th>
                                    <th className="p-2 border-b border-[#444] wrap-break-word bg-[#2a2a2a]">Categories</th>
                                </tr>
                            </thead>
                            <tbody>
                                {detailSlice.map(([title, info]) => (
                                    <tr key={title}>
                                        <td className="p-2 border-b border-[#444] wrap-break-word">
                                            <a href={wikiUrl(title)} target="_blank" rel="noopener noreferrer" className="text-[#4dabf7] no-underline hover:underline">
                                                {title}
                                            </a>
                                        </td>
                                        <td className="p-2 border-b border-[#444] wrap-break-word">{info.freq}</td>
                                        <td className="p-2 border-b border-[#444] wrap-break-word">{info.mean_depth ?? '—'}</td>
                                        <td className="p-2 border-b border-[#444] wrap-break-word">
                                            {info.categories ? (
                                                info.categories.map((cat, idx) => (
                                                    <span key={cat}>
                                                        <a href={categoryUrl(cat)} target="_blank" rel="noopener noreferrer" className="text-[#4dabf7] no-underline hover:underline">
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
                            <div className="flex justify-between items-center mt-2 pt-2">
                                <button onClick={() => setDetailOffset(Math.max(0, detailOffset - detailLimit))} disabled={!detailHasPrev} className="px-3 py-1.5 bg-[#333] text-[#e0e0e0] border border-[#555] rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">&laquo; Prev</button>
                                <span>{detailOffset + 1} - {Math.min(detailOffset + detailLimit, detailTotal)} of {detailTotal}</span>
                                <button onClick={() => setDetailOffset(detailOffset + detailLimit)} disabled={!detailHasNext} className="px-3 py-1.5 bg-[#333] text-[#e0e0e0] border border-[#555] rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">Next &raquo;</button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
