import os
from typing import Optional
from .supabase_client import get_supabase_admin

def upload_bytes(path: str, content: bytes, content_type: str, bucket: Optional[str] = None, upsert: bool = True) -> str:
    sb = get_supabase_admin()
    bucket = bucket or os.getenv("SUPABASE_STORAGE_BUCKET", "private-files")
    store = sb.storage.from_(bucket)
    store.upload(path, content, {"content-type": content_type, "upsert": upsert})
    return path

def create_signed_url(path: str, expires_in: int = 3600, bucket: Optional[str] = None) -> str:
    sb = get_supabase_admin()
    bucket = bucket or os.getenv("SUPABASE_STORAGE_BUCKET", "private-files")
    store = sb.storage.from_(bucket)
    return store.create_signed_url(path, expires_in)["signedURL"]
