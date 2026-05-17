import { useState, useEffect, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const BTN_CLASS = "px-3 py-1 bg-[#333] border border-[#555] rounded text-[#e0e0e0] cursor-pointer hover:bg-[#444] disabled:opacity-50"

export interface LoadDumpModalProps {
    showPicker: boolean;
    setShowPicker: (show: boolean) => void;
    onSuccess: (date: string) => void;
}

export function LoadDumpModal({ showPicker, setShowPicker, onSuccess }: LoadDumpModalProps) {
    const [dates, setDates] = useState<string[]>([])
    const [fetching, setFetching] = useState(true)
    const [fetchError, setFetchError] = useState('')
    const [selected, setSelected] = useState('')
    const [loading, setLoading] = useState(false)
    const [loadError, setLoadError] = useState('')

    useEffect(() => {
        if (!showPicker) return
        fetch(`${API_URL}/articles/remote-dumps`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch dumps')
                return res.json()
            })
            .then(data => {
                setDates(data.dates || [])
                setSelected(data.dates?.[0] || '')
            })
            .catch(err => setFetchError(err.message))
            .finally(() => setFetching(false))
    }, [showPicker])

    const handleLoad = useCallback(() => {
        if (!selected || loading) return
        setLoading(true)
        setLoadError('')
        fetch(`${API_URL}/articles/load?date=${selected}`, { method: 'POST' })
            .then(res => {
                if (!res.ok) return res.json().then(d => { throw new Error(d.detail || 'Failed to load') })
            })
            .then(() => {
                setShowPicker(false)
                onSuccess(selected)
            })
            .catch(err => setLoadError(err.message))
            .finally(() => setLoading(false))
    }, [selected, loading, setShowPicker, onSuccess])

    if (!showPicker) return null

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-100" onClick={() => setShowPicker(false)}>
            <div className="bg-[rgb(36,34,34)] rounded-xl px-8 py-6 flex flex-col gap-4 min-w-80 max-w-md shadow-[0_8px_32px_rgba(0,0,0,0.2)]" onClick={(e) => e.stopPropagation()}>
                <h3 className="m-0">Select dump to download</h3>
                {fetching ? (
                    <p className="text-[#888] m-0">Loading available dumps...</p>
                ) : fetchError ? (
                    <p className="text-red-500 m-0">{fetchError}</p>
                ) : dates.length === 0 ? (
                    <p className="text-[#888] m-0">No dumps available</p>
                ) : (
                    <div className="flex flex-col gap-2 max-h-60 overflow-y-auto">
                        {dates.map(date => {
                            const isSelected = selected === date
                            return (
                                <button
                                    key={date}
                                    onClick={() => setSelected(date)}
                                    disabled={loading}
                                    className={`text-left px-3 py-2 rounded border cursor-pointer ${isSelected ? 'border-[#6b8aed] bg-[#1a2a4a]' : 'border-[#555] bg-[#2a2a2a] hover:bg-[#333]'} ${loading ? 'opacity-50' : ''}`}
                                >
                                    <div className="text-[#e0e0e0] font-medium">{date}</div>
                                </button>
                            )
                        })}
                    </div>
                )}
                {loadError && (
                    <p className="text-red-500 m-0 text-sm">{loadError}</p>
                )}
                <div className="flex gap-2 justify-end">
                    <button onClick={handleLoad} disabled={!selected || fetching || loading} className={BTN_CLASS}>
                        {loading ? 'Loading...' : 'Download'}
                    </button>
                    <button onClick={() => setShowPicker(false)} disabled={loading} className={BTN_CLASS}>Cancel</button>
                </div>
            </div>
        </div>
    )
}
