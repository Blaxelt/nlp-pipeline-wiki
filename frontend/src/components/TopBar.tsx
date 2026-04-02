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
    error
}: TopBarProps) {
    return (
        <div className="top-bar">
            <p>Revision ID: {articleId}</p>
            <div className="input-container">
                <input
                    type="text"
                    placeholder="Revision ID..."
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
                <button onClick={handleSearch}>🔎</button>
                <button onClick={() => handleAdjacent('prev')}>⬅️</button>
                <button onClick={() => handleAdjacent('next')}>➡️</button>
                <button onClick={() => setShowPicker(true)}>Load bz2</button>
                <button
                    onClick={handleExtractEntities}
                    disabled={!articleId || extracting}
                    title="Extract wikilink entities and save to JSON"
                >
                    {extracting ? '⏳' : '🔗 Extract'}
                </button>
                {extractMsg && (
                    <p style={{
                        margin: 0, whiteSpace: 'nowrap', alignSelf: 'center',
                        color: extractMsg.startsWith('✅') ? 'green' : 'red'
                    }}>
                        {extractMsg}
                    </p>
                )}
                {error && (
                    <p style={{ color: 'red', margin: 0, whiteSpace: 'nowrap', alignSelf: 'center' }}>
                        {error}
                    </p>
                )}
            </div>
        </div>
    )
}
