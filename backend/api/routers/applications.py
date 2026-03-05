from fastapi import APIRouter, Header
from typing import Optional
from ..services.auth import get_current_user_id
from ..services.supabase_client import get_supabase_admin

router = APIRouter()

@router.post("/create")
def create_application(job_post_id: str, channel: Optional[str] = None, rav_countable: bool = True, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    user_id = get_current_user_id(x_user_id)
    sb = get_supabase_admin()
    res = sb.table("applications").insert({"user_id": user_id, "job_post_id": job_post_id, "status": "draft", "channel": channel, "rav_countable": rav_countable}).execute()
    return {"application": res.data[0]}

@router.post("/confirm-sent")
def confirm_sent(application_id: str, applied_at: str, proof_storage_path: Optional[str] = None, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    user_id = get_current_user_id(x_user_id)
    sb = get_supabase_admin()
    sb.table("applications").update({"status": "sent", "user_confirmed_sent": True, "applied_at": applied_at, "proof_storage_path": proof_storage_path}).eq("id", application_id).eq("user_id", user_id).execute()
    return {"ok": True}
