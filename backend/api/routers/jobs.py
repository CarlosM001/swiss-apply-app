from fastapi import APIRouter, Header
from typing import Optional
from ..services.auth import get_current_user_id
from ..services.supabase_client import get_supabase_admin

router = APIRouter()

@router.post("/create")
def create_job_post(description_text: str, company: Optional[str] = None, title: Optional[str] = None, location: Optional[str] = None, url: Optional[str] = None, x_user_id: Optional[str] = Header(default=None, alias="X-User-Id")):
    user_id = get_current_user_id(x_user_id)
    sb = get_supabase_admin()
    res = sb.table("job_posts").insert({"user_id": user_id, "source": "manual", "company": company, "title": title, "location": location, "url": url, "description_text": description_text}).execute()
    return {"job_post": res.data[0]}
