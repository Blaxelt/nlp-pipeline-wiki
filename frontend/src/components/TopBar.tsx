import { Link } from 'react-router-dom'

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
    articleId_forCompare
}: TopBarProps) {
    const btn = "px-2 py-1 shrink-0 whitespace-nowrap bg-[#333] border border-[#555] rounded text-[#e0e0e0] cursor-pointer hover:bg-[#444] disabled:opacity-50"

    return (
        <div className="flex items-center m-2.5 gap-2.5 overflow-hidden">
            <p>Revision ID: {articleId}</p>
            <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <input
                    type="text"
                    placeholder="Revision ID..."
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    className="p-0.75 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0]"
                />
                <button onClick={handleSearch} className={btn}>🔎</button>
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
                <Link to="/neologisms" className="px-2 py-1 shrink-0 whitespace-nowrap bg-transparent text-inherit border-none cursor-pointer no-underline font-inherit hover:opacity-80" title="View and filter neologisms">
                    Neologisms
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
