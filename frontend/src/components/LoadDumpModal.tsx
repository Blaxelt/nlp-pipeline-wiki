const BTN_CLASS = "px-3 py-1 bg-[#333] border border-[#555] rounded text-[#e0e0e0] cursor-pointer hover:bg-[#444] disabled:opacity-50"

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
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-100" onClick={() => setShowPicker(false)}>
            <div className="bg-[rgb(36,34,34)] rounded-xl px-8 py-6 flex flex-col gap-4 min-w-75 shadow-[0_8px_32px_rgba(0,0,0,0.2)]" onClick={(e) => e.stopPropagation()}>
                <h3 className="m-0">Select dump date</h3>
                <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="p-2 text-base border border-gray-500 rounded-md bg-[#2a2a2a] text-[#e0e0e0]"
                />
                <div className="flex gap-2 justify-end">
                    <button onClick={handleSubmit} disabled={!date || loading} className={BTN_CLASS}>
                        {loading ? 'Loading...' : 'Load'}
                    </button>
                    <button onClick={() => setShowPicker(false)} className={BTN_CLASS}>Cancel</button>
                </div>
                {modalError ? (
                    <p className="text-red-500 mt-2 text-[0.9rem]">
                        ⚠️ {modalError}
                    </p>
                ) : null}
            </div>
        </div>
    )
}
