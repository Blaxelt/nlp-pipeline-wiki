import { useState, useEffect, useRef, useCallback } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const BTN_CLASS = "px-3 py-1.5 bg-[#333] border border-[#555] rounded text-[#e0e0e0] cursor-pointer hover:bg-[#444] disabled:opacity-50"

interface PipelineStatus {
    status: 'idle' | 'running' | 'completed' | 'failed' | 'cancelled'
    elapsed_seconds?: number
    log_tail?: string[]
    pid?: number
    new_date?: string
    old_date?: string
}

function formatElapsed(seconds?: number) {
    if (seconds === undefined || seconds < 0) return '0s'
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)
    const parts = []
    if (h > 0) parts.push(`${h}h`)
    if (m > 0 || h > 0) parts.push(`${m}m`)
    parts.push(`${s}s`)
    return parts.join(' ')
}

function StatusIndicator({ status }: { status: PipelineStatus['status'] }) {
    const colorMap: Record<string, string> = {
        idle: '#888',
        running: '#4dabf7',
        completed: '#51cf66',
        failed: '#ff6b6b',
        cancelled: '#ffa94d',
    }
    const color = colorMap[status] || '#888'
    const isRunning = status === 'running'
    return (
        <div className="flex items-center gap-2">
            <span
                className="inline-block w-2.5 h-2.5 rounded-full"
                style={{
                    backgroundColor: color,
                    ...(isRunning ? { animation: 'pipeline-pulse 1.5s ease-in-out infinite' } : {}),
                }}
            />
            <style>{`@keyframes pipeline-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
            <span className="capitalize text-[#e0e0e0]">{status}</span>
        </div>
    )
}

export function PipelinePanel() {
    const [collapsed, setCollapsed] = useState(true)
    const [dumps, setDumps] = useState<string[]>([])
    
    const [newDate, setNewDate] = useState('')
    const [oldDate, setOldDate] = useState('')
    
    const [status, setStatus] = useState<PipelineStatus>({ status: 'idle' })
    const [error, setError] = useState('')
    
    const logRef = useRef<HTMLPreElement>(null)

    const fetchStatus = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/pipeline/status`)
            if (res.ok) {
                const data = await res.json()
                setStatus(data)
            }
        } catch (err) {
            console.error('Failed to fetch status', err)
        }
    }, [])

    useEffect(() => {
        // Fetch dumps
        fetch(`${API_URL}/pipeline/dumps`)
            .then(res => res.json())
            .then(data => {
                const dumpList = Array.isArray(data) ? data : (data.dumps || [])
                setDumps(dumpList)
                if (dumpList.length > 0) {
                    setNewDate(dumpList[dumpList.length - 1])
                    if (dumpList.length > 1) {
                        setOldDate(dumpList[dumpList.length - 2])
                    } else {
                        setOldDate(dumpList[0])
                    }
                }
            })
            .catch(err => console.error('Failed to fetch dumps', err))
        
        fetchStatus()
    }, [fetchStatus])

    useEffect(() => {
        let interval: ReturnType<typeof setInterval>
        if (status.status === 'running') {
            interval = setInterval(fetchStatus, 5000)
        }
        return () => {
            if (interval) clearInterval(interval)
        }
    }, [status.status, fetchStatus])

    useEffect(() => {
        if (logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight
        }
    }, [status.log_tail, collapsed])

    const handleGenerate = async () => {
        setError('')
        try {
            const res = await fetch(`${API_URL}/pipeline/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    new_date: newDate,
                    old_date: oldDate
                })
            })
            if (!res.ok) {
                const d = await res.json()
                throw new Error(d.detail || 'Failed to start pipeline')
            }
            fetchStatus()
            setCollapsed(false)
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Unknown error')
        }
    }

    const handleCancel = async () => {
        try {
            await fetch(`${API_URL}/pipeline/cancel`, { method: 'POST' })
            fetchStatus()
        } catch (err) {
            console.error('Failed to cancel pipeline', err)
        }
    }

    return (
        <div className="bg-[#1e1e1e] border border-[#444] rounded-lg mb-6 overflow-hidden">
            <div 
                className="flex justify-between items-center px-4 py-2 bg-[#2a2a2a] cursor-pointer hover:bg-[#333] border-b border-[#444]"
                onClick={() => setCollapsed(!collapsed)}
            >
                <h3 className="m-0 text-[#e0e0e0] text-sm font-semibold">Generate Dataset</h3>
                <span className="text-[#888] text-sm">{collapsed ? '▼ Expand' : '▲ Collapse'}</span>
            </div>
            
            {!collapsed && (
                <div className="p-4 text-[#e0e0e0] text-sm flex flex-col gap-4">
                    {error && <div className="text-[#ff6b6b]">⚠️ {error}</div>}
                    
                    <div className="flex flex-wrap gap-6 items-end">
                        <div className="flex flex-col gap-1">
                            <label className="text-[#aaa]">New dump:</label>
                            <select 
                                value={newDate} 
                                onChange={e => setNewDate(e.target.value)}
                                className="p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0] min-w-32"
                            >
                                {dumps.map(d => <option key={d} value={d}>{d}</option>)}
                            </select>
                        </div>
                        <div className="flex flex-col gap-1">
                            <label className="text-[#aaa]">Old dump:</label>
                            <select 
                                value={oldDate} 
                                onChange={e => setOldDate(e.target.value)}
                                className="p-1.5 bg-[#2a2a2a] border border-[#555] rounded text-[#e0e0e0] min-w-32"
                            >
                                {dumps.map(d => <option key={d} value={d}>{d}</option>)}
                            </select>
                        </div>
                    </div>
                    
                    <div className="flex gap-3">
                        <button 
                            onClick={handleGenerate} 
                            disabled={status.status === 'running'}
                            className={`${BTN_CLASS} bg-[#4dabf7] text-[#1a1a1a] border-[#4dabf7] hover:bg-[#3b8fd9] font-medium flex items-center gap-2`}
                        >
                            ▶ Generate
                        </button>
                        {status.status === 'running' && (
                            <button onClick={handleCancel} className={BTN_CLASS + " text-[#f28b8b] border-[#5c2020]"}>
                                ✕ Cancel
                            </button>
                        )}
                    </div>

                    <div className="flex items-center gap-4 mt-2 py-2 border-t border-[#333]">
                        <StatusIndicator status={status.status} />
                        {status.pid && <span className="text-[#888] text-xs">PID {status.pid}</span>}
                        {status.status !== 'idle' && status.elapsed_seconds !== undefined && (
                            <span className="text-[#888] text-xs">{formatElapsed(status.elapsed_seconds)} elapsed</span>
                        )}
                    </div>

                    <div className="border border-[#444] rounded">
                        <div className="bg-[#2a2a2a] px-3 py-1 text-xs text-[#aaa] border-b border-[#444]">
                            Pipeline Log
                        </div>
                        <pre 
                            ref={logRef}
                            className="m-0 p-3 bg-[#111] text-[#8f8] font-mono text-[0.8rem] max-h-60 overflow-y-auto whitespace-pre-wrap break-words"
                        >
                            {status.log_tail && status.log_tail.length > 0 ? status.log_tail.join('\n') : 'No logs yet.'}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    )
}
