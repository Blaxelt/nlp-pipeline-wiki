import { useState, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const BTN_CLASS = "px-3 py-1 bg-[#333] border border-[#555] rounded text-[#e0e0e0] cursor-pointer hover:bg-[#444] disabled:opacity-50"

export interface DumpSelectModalProps {
    onLoad: (date: string) => void
    onClose: () => void
    currentDump: string | null
}

export function DumpSelectModal({ onLoad, onClose, currentDump }: DumpSelectModalProps) {
    const [dumps, setDumps] = useState<string[]>([])
    const [fetchingDumps, setFetchingDumps] = useState(true)
    const [fetchError, setFetchError] = useState('')
    const [selected, setSelected] = useState<string>(currentDump || '')
    const [loaded, setLoaded] = useState(false)
    const [loadingDump, setLoadingDump] = useState(false)
    const [loadError, setLoadError] = useState('')

    if (!loaded) {
        setLoaded(true)
        fetch(`${API_URL}/articles/available-dumps`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch dumps')
                return res.json()
            })
            .then(data => {
                setDumps(data.available || [])
                setSelected(data.current || (data.available.length > 0 ? data.available[0] : ''))
            })
            .catch(err => setFetchError(err.message))
            .finally(() => setFetchingDumps(false))
    }

    const handleLoad = useCallback(() => {
        if (!selected || loadingDump) return
        setLoadingDump(true)
        setLoadError('')
        fetch(`${API_URL}/articles/load-existing?date=${selected}`, { method: 'POST' })
            .then(res => {
                if (!res.ok) return res.json().then(d => { throw new Error(d.detail || 'Failed to load') })
            })
            .then(() => onLoad(selected))
            .catch(err => setLoadError(err.message))
            .finally(() => setLoadingDump(false))
    }, [selected, loadingDump, onLoad])

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-100" onClick={onClose}>
            <div className="bg-[rgb(36,34,34)] rounded-xl px-8 py-6 flex flex-col gap-4 min-w-80 max-w-md shadow-[0_8px_32px_rgba(0,0,0,0.2)]" onClick={e => e.stopPropagation()}>
                <h3 className="m-0 text-lg">Select dump to load</h3>
                {fetchingDumps ? (
                    <p className="text-[#888] m-0">Loading available dumps...</p>
                ) : fetchError ? (
                    <p className="text-red-500 m-0">{fetchError}</p>
                ) : dumps.length === 0 ? (
                    <p className="text-[#888] m-0">No dumps found in data/ directory</p>
                ) : (
                    <div className="flex flex-col gap-2 max-h-60 overflow-y-auto">
                        {dumps.map(date => {
                            const isSelected = selected === date
                            return (
                                <button
                                    key={date}
                                    onClick={() => setSelected(date)}
                                    disabled={loadingDump}
                                    className={`text-left px-3 py-2 rounded border cursor-pointer ${isSelected ? 'border-[#6b8aed] bg-[#1a2a4a]' : 'border-[#555] bg-[#2a2a2a] hover:bg-[#333]'} ${loadingDump ? 'opacity-50' : ''}`}
                                >
                                    <div className="text-[#e0e0e0] font-medium">
                                        {date}
                                        {date === currentDump ? ' (loaded)' : ''}
                                    </div>
                                </button>
                            )
                        })}
                    </div>
                )}
                {loadError && (
                    <p className="text-red-500 m-0 text-sm">{loadError}</p>
                )}
                <div className="flex gap-2 justify-end">
                    <button onClick={handleLoad} disabled={!selected || fetchingDumps || loadingDump} className={BTN_CLASS}>
                        {loadingDump ? 'Loading...' : 'Load'}
                    </button>
                    <button onClick={onClose} disabled={loadingDump} className={BTN_CLASS}>Close</button>
                </div>
            </div>
        </div>
    )
}