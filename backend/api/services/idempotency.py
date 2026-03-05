from typing import Optional
from .supabase_client import get_supabase_admin

def find_existing_job(user_id: str, task_type: str, idempotency_key: Optional[str]) -> Optional[dict]:
    if not idempotency_key:
        return None
    sb = get_supabase_admin()
    res = (sb.table("job_tasks")
             .select("*")
             .eq("user_id", user_id)
             .eq("task_type", task_type)
             .eq("idempotency_key", idempotency_key)
             .limit(1)
             .execute())
    data = res.data or []
    return data[0] if data else None

def create_job_task(user_id: str, task_type: str, input_payload: dict, idempotency_key: Optional[str]) -> dict:
    sb = get_supabase_admin()
    payload = {"user_id": user_id, "task_type": task_type, "status": "queued", "idempotency_key": idempotency_key, "input": input_payload, "output": {}}
    res = sb.table("job_tasks").insert(payload).execute()
    return res.data[0]

def set_job_task(job_task_id: str, status: str, output: Optional[dict] = None, error: Optional[str] = None) -> None:
    sb = get_supabase_admin()
    update = {"status": status}
    if output is not None:
        update["output"] = output
    if error is not None:
        update["error"] = error
    sb.table("job_tasks").update(update).eq("id", job_task_id).execute()
