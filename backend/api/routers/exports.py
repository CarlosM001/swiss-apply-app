from fastapi import APIRouter, BackgroundTasks, Header
from typing import Optional
from ..services.auth import get_current_user_id
from ..services.idempotency import find_existing_job, create_job_task
from ..background.jobs import run_rav_export

router = APIRouter()

@router.post("/rav")
def create_rav_export(period_start: str, period_end: str, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"), x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"), background_tasks: BackgroundTasks = None):
    user_id = get_current_user_id(x_user_id)
    existing = find_existing_job(user_id, "export_rav", idempotency_key)
    if existing:
        return {"job_task_id": existing["id"], "status": existing["status"], "reused": True}
    job = create_job_task(user_id, "export_rav", {"period_start": period_start, "period_end": period_end}, idempotency_key)
    background_tasks.add_task(run_rav_export, job["id"], user_id, period_start, period_end)
    return {"job_task_id": job["id"], "status": "queued"}
