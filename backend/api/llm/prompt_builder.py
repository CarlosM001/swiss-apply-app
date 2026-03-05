import json
from typing import Dict, Any

def build_single_call_prompt(cv_profile: Dict[str, Any], job_post: Dict[str, Any]) -> str:
    cv = json.dumps(cv_profile, ensure_ascii=False, indent=2, sort_keys=True)
    jp = json.dumps(job_post, ensure_ascii=False, indent=2, sort_keys=True)

    return f"""
Write the BODY-ONLY text for a Swiss cover letter in de-CH.

Candidate (JSON):
{cv}

Job posting (JSON):
{jp}

Rules:
- BODY ONLY (no header/subject/date/closing/signature)
- 2–3 paragraphs, separated by exactly one blank line
- 150–240 words
- No bullet points
- Never invent facts; omit unknown details
- End with a polite invitation to an interview (still body-only)
""".strip()