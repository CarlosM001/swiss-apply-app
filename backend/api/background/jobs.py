from __future__ import annotations
from datetime import datetime
from typing import Optional

from ..services.supabase_client import get_supabase_admin
from ..services.idempotency import set_job_task
from ..services.storage import upload_bytes

# --- NEUE IMPORTS FÜR DEN LLM-CLIENT ---
from ..llm.llm_client import generate_cover_letter_body_only
from ..llm.prompt_builder import build_single_call_prompt

from ..decision.mode_switch import decide_mode
from ..multi_agents.pipeline import run_multi_agent_pipeline
from backend.shared.utils.docx_builder import build_cover_letter_docx, SwissLetterHeader
from backend.shared.utils.pdf_builder import build_rav_pdf
from backend.shared.utils.xlsx_builder import build_rav_xlsx

def _now_ch() -> str:
    return datetime.now().strftime("%d.%m.%Y")

def run_generate_letter(job_task_id: str, user_id: str, application_id: str, model: Optional[str] = None) -> None:
    sb = get_supabase_admin()
    try:
        set_job_task(job_task_id, "running")
        app = sb.table("applications").select("id,job_post_id").eq("id", application_id).eq("user_id", user_id).single().execute().data
        job = sb.table("job_posts").select("*").eq("id", app["job_post_id"]).eq("user_id", user_id).single().execute().data
        profile = sb.table("profiles").select("*").eq("user_id", user_id).single().execute().data

        cv_profile = {"personal": {"full_name": profile.get("full_name")}, "skills": [], "experience": [], "languages": []}
        job_post = {"title": job.get("title"), "company": job.get("company"), "location": job.get("location"), "requirements": {"keywords": []}, "swiss": {"language_requirements": []}}
        
        # Der Risk-Score entscheidet (Single vs. Multi)
        decision = decide_mode(cv_profile, job_post)

        # --- NEUE SINGLE-CALL LOGIK ---
        prompt = build_single_call_prompt(cv_profile, job_post)
        
        if decision.mode == "multi":
            multi = run_multi_agent_pipeline(cv_profile=cv_profile, job_post=job_post, model=model)
            body = multi["body_text"]
        else:
            # Hier greift unser neuer, superschneller LiteLLM-Client!
            llm_result = generate_cover_letter_body_only(prompt=prompt, model=model)
            body = llm_result.body_text
        # ------------------------------

        header = SwissLetterHeader(
            full_name=profile.get("full_name") or "",
            street=profile.get("street") or "",
            postal_code=profile.get("postal_code") or "",
            city=profile.get("location_city") or "",
            phone=profile.get("phone"),
            email=profile.get("email"),
        )
        
        recipient = f"{job.get('company') or ''}\nPersonalabteilung\n{job.get('location') or ''}".strip()
        place_and_date = f"{profile.get('location_city') or ''}, {_now_ch()}"
        subject = f"Bewerbung als {job.get('title') or 'Position'}"

        # --- UNSER UNANGREIFBARER DOCX BUILDER ---
        docx_bytes = build_cover_letter_docx(
            header=header, 
            recipient_block=recipient, 
            place_and_date=place_and_date, 
            subject=subject, 
            body_text=body, 
            signature_name=header.full_name
        )

        latest = (sb.table("letters").select("version").eq("application_id", application_id).order("version", desc=True).limit(1).execute()).data
        next_version = (latest[0]["version"] + 1) if latest else 1

        storage_key = f"letters/{user_id}/{application_id}/letter_v{next_version}.docx"
        
        # Dokument in Supabase Storage hochladen
        upload_bytes(storage_key, docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        # Metadaten in der Datenbank speichern
        sb.table("letters").insert({
            "application_id": application_id,
            "user_id": user_id,
            "language": "de-CH",
            "version": next_version,
            "content": body,
            "claims_used": [],
            "open_questions": [],
            "approved_by_user": False,
            "docx_storage_path": storage_key,
        }).execute()

        set_job_task(job_task_id, "done", output={"mode": decision.mode, "risk_score": decision.risk_score, "reasons": decision.reasons, "docx_storage_path": storage_key, "letter_version": next_version})
    except Exception as e:
        set_job_task(job_task_id, "failed", error=str(e))

def run_rav_export(job_task_id: str, user_id: str, period_start: str, period_end: str) -> None:
    sb = get_supabase_admin()
    try:
        set_job_task(job_task_id, "running")
        apps = (sb.table("applications")
                  .select("id, applied_at, channel, status, proof_storage_path, notes, job_posts(company,title,location)")
                  .eq("user_id", user_id)
                  .eq("rav_countable", True)
                  .eq("user_confirmed_sent", True)
                  .gte("applied_at", period_start)
                  .lte("applied_at", period_end)
                  .execute()).data or []

        rows = []
        for a in apps:
            jp = a.get("job_posts") or {}
            rows.append({"date": (a.get("applied_at") or "")[:10], "company": jp.get("company",""), "title": jp.get("title",""), "location": jp.get("location",""), "channel": a.get("channel",""), "status": a.get("status",""), "proof": a.get("proof_storage_path",""), "notes": a.get("notes","")})

        pdf_bytes = build_rav_pdf("Arbeitsbemühungen (RAV)", f"Zeitraum: {period_start} bis {period_end}", rows)
        xlsx_bytes = build_rav_xlsx(rows)

        pdf_key = f"rav/{user_id}/{period_start}_{period_end}/arbeitsbemuehungen.pdf"
        xlsx_key = f"rav/{user_id}/{period_start}_{period_end}/arbeitsbemuehungen.xlsx"
        upload_bytes(pdf_key, pdf_bytes, "application/pdf")
        upload_bytes(xlsx_key, xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        sb.table("rav_exports").insert({"user_id": user_id, "period_start": period_start, "period_end": period_end, "export_path_pdf": pdf_key, "export_path_xlsx": xlsx_key}).execute()

        set_job_task(job_task_id, "done", output={"count": len(rows), "export_path_pdf": pdf_key, "export_path_xlsx": xlsx_key})
    except Exception as e:
        set_job_task(job_task_id, "failed", error=str(e))