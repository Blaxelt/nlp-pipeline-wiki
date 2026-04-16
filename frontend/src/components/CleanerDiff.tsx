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
            <div className="diff-overlay">
                <div className="diff-modal">
                    <p>⏳ Fetching and cleaning with all 3 libraries…</p>
                </div>
            </div>
        )
    }

    if (!results) return null

    return (
        <div className="diff-overlay">
            <div className="diff-modal">
                <div className="diff-header">
                    <h3>Cleaner Comparison</h3>
                    <button onClick={onClose}>✕</button>
                </div>

                <div className="diff-selectors">
                    <label>
                        Base:
                        <select value={baseLib} onChange={e => setBaseLib(e.target.value as LibraryName)}>
                            {libs.map(l => <option key={l} value={l}>{LABELS[l]}</option>)}
                        </select>
                    </label>
                    <span>vs</span>
                    <label>
                        Compare:
                        <select value={compareLib} onChange={e => setCompareLib(e.target.value as LibraryName)}>
                            {libs.filter(l => l !== baseLib).map(l => <option key={l} value={l}>{LABELS[l]}</option>)}
                        </select>
                    </label>
                </div>

                <div className="diff-content">
                    {diffParts && diffParts.map((part, i) => (
                        <span
                            key={i}
                            className={part.added ? 'diff-added' : part.removed ? 'diff-removed' : ''}
                        >
                            {part.value}
                        </span>
                    ))}
                </div>

                <div className="diff-legend">
                    <span className="diff-removed">■ Only in {LABELS[baseLib]}</span>
                    <span className="diff-added">■ Only in {LABELS[compareLib]}</span>
                </div>
            </div>
        </div>
    )
}
