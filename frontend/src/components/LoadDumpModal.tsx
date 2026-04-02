export interface LoadDumpModalProps {
    showPicker: boolean;
    setShowPicker: (show: boolean) => void;
    date: string;
    setDate: (date: string) => void;
    handleSubmit: () => void;
    loading: boolean;
    modalError: string;
}

export function LoadDumpModal({
    showPicker,
    setShowPicker,
    date,
    setDate,
    handleSubmit,
    loading,
    modalError
}: LoadDumpModalProps) {
    if (!showPicker) return null;

    return (
        <div className="modal-overlay" onClick={() => setShowPicker(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
                <h3>Select dump date</h3>
                <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                />
                <div className="modal-actions">
                    <button onClick={handleSubmit} disabled={!date || loading}>
                        {loading ? 'Loading...' : 'Load'}
                    </button>
                    <button onClick={() => setShowPicker(false)}>Cancel</button>
                </div>
                {modalError && (
                    <p style={{ color: 'red', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                        ⚠️ {modalError}
                    </p>
                )}
            </div>
        </div>
    )
}
