from fastapi import APIRouter, BackgroundTasks, Header
from typing import Optional
from ..services.auth import get_current_user_id
from ..services.idempotency import find_existing_job, create_job_task
from ..background.jobs import run_generate_letter

router = APIRouter()

@router.post("/generate")
def generate_letter(application_id: str, model: Optional[str] = None, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"), x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"), background_tasks: BackgroundTasks = None):
    user_id = get_current_user_id(x_user_id)
    existing = find_existing_job(user_id, "letter_generate", idempotency_key)
    if existing:
        return {"job_task_id": existing["id"], "status": existing["status"], "reused": True}
    job = create_job_task(user_id, "letter_generate", {"application_id": application_id, "model": model}, idempotency_key)
    background_tasks.add_task(run_generate_letter, job["id"], user_id, application_id, model)
    return {"job_task_id": job["id"], "status": "queued"}
