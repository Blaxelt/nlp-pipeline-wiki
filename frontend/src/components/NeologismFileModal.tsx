import { useState, useEffect, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const BTN_CLASS = "px-3 py-1 bg-[#333] border border-[#555] rounded text-[#e0e0e0] cursor-pointer hover:bg-[#444] disabled:opacity-50"

interface FileEntry {
    path: string
    name: string
}

export interface NeologismFileModalProps {
    onLoad: () => void
    onClose: () => void
}

export function NeologismFileModal({ onLoad, onClose }: NeologismFileModalProps) {
    const [wordsFiles, setWordsFiles] = useState<FileEntry[]>([])
    const [phrasalFiles, setPhrasalFiles] = useState<FileEntry[]>([])
    const [current, setCurrent] = useState<{ words: string | null; phrasal: string | null }>({ words: null, phrasal: null })
    const [fetching, setFetching] = useState(true)
    const [fetchError, setFetchError] = useState('')
    const [selected, setSelected] = useState<{ type: 'words' | 'phrasal'; path: string } | null>(null)
    const [loading, setLoading] = useState(false)
    const [loadError, setLoadError] = useState('')

    useEffect(() => {
        fetch(`${API_URL}/neologisms/available-files`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch files')
                return res.json()
            })
            .then(data => {
                setWordsFiles(data.words || [])
                setPhrasalFiles(data.phrasal || [])
                setCurrent(data.current || { words: null, phrasal: null })
            })
            .catch(err => setFetchError(err.message))
            .finally(() => setFetching(false))
    }, [])

    const handleLoad = useCallback(() => {
        if (!selected || loading) return
        setLoading(true)
        setLoadError('')
        fetch(`${API_URL}/neologisms/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: selected.type, path: selected.path }),
        })
            .then(res => {
                if (!res.ok) return res.json().then(d => { throw new Error(d.detail || 'Failed to load') })
                return res.json()
            })
            .then(() => {
                setCurrent(prev => ({ ...prev, [selected.type]: selected.path }))
                onLoad()
                onClose()
            })
            .catch(err => setLoadError(err.message))
            .finally(() => setLoading(false))
    }, [selected, loading, onLoad, onClose])

    const totalFiles = wordsFiles.length + phrasalFiles.length

    const renderFileList = (files: FileEntry[], type: 'words' | 'phrasal', label: string) => {
        if (files.length === 0) return null
        return (
            <div className="flex flex-col gap-1">
                <h4 className="m-0 text-[0.85rem] text-[#aaa] uppercase tracking-wide">{label}</h4>
                <div className="flex flex-col gap-1">
                    {files.map(f => {
                        const isSelected = selected?.type === type && selected?.path === f.path
                        const isCurrent = current[type] === f.path
                        return (
                            <button
                                key={f.path}
                                onClick={() => setSelected({ type, path: f.path })}
                                disabled={loading}
                                className={`text-left px-3 py-2 rounded border cursor-pointer ${isSelected ? 'border-[#6b8aed] bg-[#1a2a4a]' : 'border-[#555] bg-[#2a2a2a] hover:bg-[#333]'} ${loading ? 'opacity-50' : ''}`}
                            >
                                <div className="text-[#e0e0e0] font-medium text-[0.85rem]">
                                    {f.name}
                                    {isCurrent ? <span className="text-[#888] ml-1">(loaded)</span> : null}
                                </div>
                                <div className="text-[#666] text-[0.75rem] mt-0.5">{f.path}</div>
                            </button>
                        )
                    })}
                </div>
            </div>
        )
    }

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-100" onClick={onClose}>
            <div className="bg-[rgb(36,34,34)] rounded-xl px-8 py-6 flex flex-col gap-4 min-w-80 max-w-lg shadow-[0_8px_32px_rgba(0,0,0,0.2)]" onClick={e => e.stopPropagation()}>
                <h3 className="m-0 text-lg">Select neologism file</h3>
                {fetching ? (
                    <p className="text-[#888] m-0">Scanning files...</p>
                ) : fetchError ? (
                    <p className="text-red-500 m-0">{fetchError}</p>
                ) : totalFiles === 0 ? (
                    <p className="text-[#888] m-0">No neologism files found in data/</p>
                ) : (
                    <div className="flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
                        {renderFileList(wordsFiles, 'words', 'Single Words')}
                        {renderFileList(phrasalFiles, 'phrasal', 'Phrasal Nouns')}
                    </div>
                )}
                {loadError && (
                    <p className="text-red-500 m-0 text-sm">{loadError}</p>
                )}
                <div className="flex gap-2 justify-end">
                    <button onClick={handleLoad} disabled={!selected || fetching || loading} className={BTN_CLASS}>
                        {loading ? 'Loading...' : 'Load'}
                    </button>
                    <button onClick={onClose} disabled={loading} className={BTN_CLASS}>Close</button>
                </div>
            </div>
        </div>
    )
}
