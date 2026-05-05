import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface TopBarProps {
    articleId: string;
    inputValue: string;
    setInputValue: (value: string) => void;
    handleSearch: () => void;
    handleAdjacent: (direction: 'next' | 'prev') => void;
    setShowPicker: (show: boolean) => void;
    handleExtractEntities: () => void;
    extracting: boolean;
    extractMsg: string;
    error: string;
    handleCompareCleaners: () => void;
    articleId_forCompare: string;
    onSelectTitle: (title: string) => void;
}

export function TopBar({
    articleId,
    inputValue,
    setInputValue,
    handleSearch,
    handleAdjacent,
    setShowPicker,
    handleExtractEntities,
    extracting,
    extractMsg,
    error,
    handleCompareCleaners,
    articleId_forCompare,
    onSelectTitle
}: TopBarProps) {
    const btn = "px-2 py-1 shrink-0 whitespace-nowrap bg-[#333] border border-[#555] rounded text-[#e0e0e0] cursor-pointer hover:bg-[#444] disabled:opacity-50"

    const [suggestions, setSuggestions] = useState<{title: string; revision_id: string}[]>([])
    const [showSuggestions, setShowSuggestions] = useState(false)
    const [suggestLoading, setSuggestLoading] = useState(false)
    const suggestionsRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)
    const requestIdRef = useRef(0)

    // Debounced suggestion fetch with stale-request guard
    useEffect(() => {
        if (!inputValue.trim() || inputValue.trim().length < 2) {
            setSuggestions([])
            setShowSuggestions(false)
            setSuggestLoading(false)
            return
        }

        const currentId = ++requestIdRef.current
        setSuggestions([])
        setSuggestLoading(true)

        const timer = setTimeout(async () => {
            try {
                const res = await fetch(
                    `${API_URL}/articles/suggest?q=${encodeURIComponent(inputValue.trim())}&limit=10`
                )
                if (currentId !== requestIdRef.current) return
                if (!res.ok) throw new Error()
                const data = await res.json()
                if (currentId !== requestIdRef.current) return
                setSuggestions(data.results || [])
                if (inputRef.current === document.activeElement) {
                    setShowSuggestions(true)
                }
            } catch {
                if (currentId !== requestIdRef.current) return
                setSuggestions([])
            } finally {
                if (currentId === requestIdRef.current) {
                    setSuggestLoading(false)
                }
            }
        }, 300)

        return () => clearTimeout(timer)
    }, [inputValue])

    // Close suggestions on click outside
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (
                suggestionsRef.current &&
                !suggestionsRef.current.contains(e.target as Node) &&
                inputRef.current &&
                !inputRef.current.contains(e.target as Node)
            ) {
                setShowSuggestions(false)
            }
        }
        document.addEventListener('mousedown', handleClick)
        return () => document.removeEventListener('mousedown', handleClick)
    }, [])

    const handleSelect = useCallback((title: string) => {
        setSuggestions([])
        setShowSuggestions(false)
        onSelectTitle(title)
    }, [onSelectTitle])

    const doSearch = () => {
        setShowSuggestions(false)
        handleSearch()
    }

    return (
        <div className="flex items-center m-2.5 gap-2.5 flex-wrap">
            <p>Revision ID: {articleId}</p>
            <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <div className="relative flex items-center gap-2.5">
                    <input
                        ref={inputRef}
                        type="text"
                        placeholder="Revision ID or title..."
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                doSearch()
                            } else if (e.key === 'Escape') {
                                setShowSuggestions(false)
                            }
                        }}
                        onFocus={() => {
                            if (inputValue.trim().length >= 2 && suggestions.length > 0) {
                                setShowSuggestions(true)
                            }
                        }}
                        className="p-[3px] bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0] w-72"
                    />
                    {showSuggestions && (
                        <div
                            ref={suggestionsRef}
                            className="absolute top-full left-0 mt-1 w-72 max-h-60 overflow-y-auto bg-[#2a2a2a] border border-[#555] rounded shadow-lg z-50"
                        >
                            {suggestLoading && (
                                <div className="px-3 py-2 text-[#888] text-sm">Loading…</div>
                            )}
                            {!suggestLoading && suggestions.length === 0 && (
                                <div className="px-3 py-2 text-[#888] text-sm">No results</div>
                            )}
                            {suggestions.map((s) => (
                                <button
                                    key={s.revision_id}
                                    onClick={() => handleSelect(s.title)}
                                    className="w-full text-left px-3 py-2 text-sm text-[#e0e0e0] hover:bg-[#444] cursor-pointer border-b border-[#444] last:border-b-0 bg-transparent"
                                >
                                    {s.title.replace(/_/g, ' ')}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
                <button onClick={doSearch} className={btn}>Load R-ID</button>
                <button onClick={() => handleAdjacent('prev')} className={btn}>⬅️</button>
                <button onClick={() => handleAdjacent('next')} className={btn}>➡️</button>
                <button onClick={() => setShowPicker(true)} className={btn}>Load bz2</button>
                <button
                    onClick={handleExtractEntities}
                    disabled={!articleId || extracting}
                    title="Extract wikilink entities and save to JSON"
                    className={btn}
                >
                    {extracting ? 'Extrayendo...' : 'Extract'}
                </button>
                <button
                    onClick={handleCompareCleaners}
                    disabled={!articleId_forCompare}
                    title="Compare output of the 3 cleaning libraries"
                    className={btn}
                >
                    Compare
                </button>
                <Link to="/neologisms">
                    <button className={btn}>    
                        Neologisms
                    </button>
                </Link>

                {extractMsg && (
                    <p className={`m-0 whitespace-nowrap self-center ${extractMsg.startsWith('✅') ? 'text-green-500' : 'text-red-500'}`}>
                        {extractMsg}
                    </p>
                )}
                {error && (
                    <p className="text-red-500 m-0 whitespace-nowrap self-center">
                        {error}
                    </p>
                )}
            </div>
        </div>
    )
}
