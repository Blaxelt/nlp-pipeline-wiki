import { useState, useMemo } from 'react'
import { diffWords } from 'diff'

interface CleanerResults {
    wikitextparser: string
    mwparserfromhell: string
    wikiextractor: string
}

type LibraryName = keyof CleanerResults

const LABELS: Record<LibraryName, string> = {
    wikitextparser: 'wikitextparser',
    mwparserfromhell: 'mwparserfromhell',
    wikiextractor: 'wikiextractor',
}

interface Props {
    results: CleanerResults | null
    loading: boolean
    onClose: () => void
}

export function CleanerDiff({ results, loading, onClose }: Props) {
    const libs = Object.keys(LABELS) as LibraryName[]
    const [baseLib, setBaseLib] = useState<LibraryName>('wikitextparser')
    const [compareLib, setCompareLib] = useState<LibraryName>('mwparserfromhell')

    const diffParts = useMemo(() => {
        if (!results) return null
        return diffWords(results[baseLib], results[compareLib])
    }, [results, baseLib, compareLib])

    if (loading) {
        return (
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-200">
                <div className="bg-[#1e1e1e] rounded-xl px-6 py-5 w-[85vw] max-h-[85vh] flex flex-col gap-3 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
                    <p>⏳ Fetching and cleaning with all 3 libraries…</p>
                </div>
            </div>
        )
    }

    if (!results) return null

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-200">
            <div className="bg-[#1e1e1e] rounded-xl px-6 py-5 w-[85vw] max-h-[85vh] flex flex-col gap-3 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
                <div className="flex justify-between items-center">
                    <h3 className="m-0 text-[#e0e0e0]">Cleaner Comparison</h3>
                    <button onClick={onClose} className="bg-transparent border-none text-[#aaa] text-xl cursor-pointer">✕</button>
                </div>

                <div className="flex items-center gap-3 text-[#ccc]">
                    <label>
                        Base:
                        <select value={baseLib} onChange={e => setBaseLib(e.target.value as LibraryName)} className="ml-1.5 px-2 py-1 rounded-md border border-[#555] bg-[#2a2a2a] text-[#e0e0e0]">
                            {libs.map(l => <option key={l} value={l}>{LABELS[l]}</option>)}
                        </select>
                    </label>
                    <span>vs</span>
                    <label>
                        Compare:
                        <select value={compareLib} onChange={e => setCompareLib(e.target.value as LibraryName)} className="ml-1.5 px-2 py-1 rounded-md border border-[#555] bg-[#2a2a2a] text-[#e0e0e0]">
                            {libs.filter(l => l !== baseLib).map(l => <option key={l} value={l}>{LABELS[l]}</option>)}
                        </select>
                    </label>
                </div>

                <div className="flex-1 overflow-y-auto whitespace-pre-wrap font-mono text-[0.85rem] leading-relaxed text-[#d4d4d4] bg-[#252525] p-4 rounded-lg">
                    {diffParts && diffParts.map((part, i) => (
                        <span
                            key={i}
                            className={part.added ? 'bg-[rgba(40,167,69,0.3)] text-[#7ce87c]' : part.removed ? 'bg-[rgba(220,53,69,0.3)] text-[#f28b8b] line-through' : ''}
                        >
                            {part.value}
                        </span>
                    ))}
                </div>

                <div className="flex gap-5 text-[0.8rem]">
                    <span className="bg-[rgba(220,53,69,0.3)] text-[#f28b8b] line-through">■ Only in {LABELS[baseLib]}</span>
                    <span className="bg-[rgba(40,167,69,0.3)] text-[#7ce87c]">■ Only in {LABELS[compareLib]}</span>
                </div>
            </div>
        </div>
    )
}
