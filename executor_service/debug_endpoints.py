from fastapi import APIRouter
from executor_service.trade_logger import trade_logger, JOURNAL_FILE
from executor_service.scheduler import scheduler
import pandas as pd
import os

router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/csv")
def get_csv_head():
    """Returns the first 5 and last 5 lines of the journal CSV."""
    if not os.path.exists(JOURNAL_FILE):
        return {"status": "FILE_NOT_FOUND", "path": JOURNAL_FILE}
    
    try:
        df = pd.read_csv(JOURNAL_FILE)
        return {
            "status": "EXISTS",
            "rows": len(df),
            "columns": list(df.columns),
            "head": df.head(5).to_dict(orient="records"),
            "tail": df.tail(5).to_dict(orient="records")
        }
    except Exception as e:
        return {"status": "READ_ERROR", "error": str(e)}

@router.get("/scheduler")
def get_scheduler_status():
    """Returns the status of the APScheduler and list of jobs."""
    jobs = []
    try:
        job_list = scheduler.get_jobs()
        for j in job_list:
            jobs.append({
                "id": j.id,
                "next_run": str(j.next_run_time),
                "func": j.func.__name__
            })
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
        
    return {
        "running": scheduler.running,
        "job_count": len(jobs),
        "jobs": jobs
    }

@router.post("/hydrate")
def force_hydrate():
    """Triggers hydration manually."""
    try:
        trade_logger.hydrate_history()
        return {"status": "HYDRATION_TRIGGERED"}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
