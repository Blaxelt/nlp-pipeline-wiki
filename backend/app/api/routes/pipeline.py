import threading
import subprocess
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
_PROJECT_ROOT = _DATA_DIR.parent
_LOGS_DIR = _PROJECT_ROOT / "logs"

_pipeline_state: dict = {
    "status": "idle",  # idle | running | completed | failed | cancelled
    "process": None,   # subprocess.Popen
    "pid": None,
    "new_date": None,
    "old_date": None,
    "started_at": None,  # datetime
    "finished_at": None, # datetime
    "exit_code": None,
    "log_file": None,    # Path to stdout log
    "log_handle": None,  # open file handle
}
_pipeline_lock = threading.Lock()

class PipelineStartRequest(BaseModel):
    new_date: str
    old_date: str

def _validate_date(date_str: str) -> bool:
    return bool(re.match(r"^\d{8}$", date_str))

@router.get("/pipeline/dumps")
def get_dumps():
    """Scan data/ for dump dates."""
    dates: set[str] = set()
    if not _DATA_DIR.exists():
        return []
    # Patterns produced by different parts of the project
    patterns = [
        re.compile(r"^eswiki-(\d{8})-pages-articles-ns0-clean\.json$"),
        re.compile(r"^eswiki-(\d{8})-pages-articles\.json$"),
    ]
    for file in _DATA_DIR.iterdir():
        if not file.is_file():
            continue
        for pat in patterns:
            m = pat.match(file.name)
            if m:
                dates.add(m.group(1))
    # Also check outputs/filtered_dumps/ (produced by run_pipeline stage 0)
    filtered_dir = _DATA_DIR / "outputs" / "filtered_dumps"
    if filtered_dir.is_dir():
        pat = re.compile(r"^eswiki-(\d{8})-pages-articles-ns0-no-redirects-clean\.json$")
        for file in filtered_dir.iterdir():
            m = pat.match(file.name)
            if m:
                dates.add(m.group(1))
    return sorted(dates)

def _monitor_process(proc, log_handle):
    proc.wait()
    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            if proc.returncode == 0:
                _pipeline_state["status"] = "completed"
            else:
                _pipeline_state["status"] = "failed"
            _pipeline_state["exit_code"] = proc.returncode
            _pipeline_state["finished_at"] = datetime.now()
        if log_handle:
            try:
                log_handle.close()
            except Exception:
                pass
            _pipeline_state["log_handle"] = None
        _pipeline_state["process"] = None

@router.post("/pipeline/start")
def start_pipeline(req: PipelineStartRequest):
    if not _validate_date(req.new_date) or not _validate_date(req.old_date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD.")
    
    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            raise HTTPException(status_code=409, detail="Pipeline is already running.")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = _LOGS_DIR / f"pipeline_{req.new_date}_{timestamp}_stdout.log"
        
        try:
            log_handle = open(log_path, "w")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to open log file: {e}")
            
        cmd = [sys.executable, "scripts/run_pipeline.py", "--date", req.new_date, "--old-date", req.old_date]
            
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(_PROJECT_ROOT),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
        except Exception as e:
            log_handle.close()
            raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {e}")
            
        _pipeline_state.update({
            "status": "running",
            "process": proc,
            "pid": proc.pid,
            "new_date": req.new_date,
            "old_date": req.old_date,
            "started_at": datetime.now(),
            "finished_at": None,
            "exit_code": None,
            "log_file": str(log_path),
            "log_handle": log_handle,
        })
        
        thread = threading.Thread(target=_monitor_process, args=(proc, log_handle), daemon=True)
        thread.start()
        
        return {
            "status": "running",
            "pid": proc.pid,
            "log_file": str(log_path)
        }

@router.get("/pipeline/status")
def get_pipeline_status():
    with _pipeline_lock:
        status = _pipeline_state["status"]
        if status == "idle":
            return {"status": "idle"}
            
        now = datetime.now()
        started_at = _pipeline_state["started_at"]
        finished_at = _pipeline_state["finished_at"]
        
        if status == "running":
            elapsed = int((now - started_at).total_seconds())
        else:
            elapsed = int((finished_at - started_at).total_seconds()) if finished_at else None
            
        log_tail = []
        log_file = _pipeline_state["log_file"]
        if log_file and Path(log_file).exists():
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    log_tail = [line.rstrip('\n') for line in lines[-80:]]
            except Exception:
                pass
                
        return {
            "status": status,
            "pid": _pipeline_state["pid"],
            "new_date": _pipeline_state["new_date"],
            "old_date": _pipeline_state["old_date"],
            "started_at": started_at.isoformat() if started_at else None,
            "elapsed_seconds": elapsed,
            "exit_code": _pipeline_state["exit_code"],
            "log_tail": log_tail
        }

@router.post("/pipeline/cancel")
def cancel_pipeline():
    with _pipeline_lock:
        if _pipeline_state["status"] != "running":
            raise HTTPException(status_code=400, detail="Pipeline is not running.")
            
        proc = _pipeline_state["process"]
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                
            _pipeline_state["status"] = "cancelled"
            _pipeline_state["finished_at"] = datetime.now()
            
        return {"status": "cancelled"}
