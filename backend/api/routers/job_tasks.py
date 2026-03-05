from fastapi import APIRouter, Header
from typing import Optional
from ..services.auth import get_current_user_id
from ..services.supabase_client import get_supabase_admin

router = APIRouter()

@router.get("/{job_task_id}")
def get_job_task(job_task_id: str, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    user_id = get_current_user_id(x_user_id)
    sb = get_supabase_admin()
    job = sb.table("job_tasks").select("*").eq("id", job_task_id).eq("user_id", user_id).single().execute().data
    return {"job": job}
