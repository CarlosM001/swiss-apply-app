from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
import json

from ..llm.llm_client import single_call_body_only
from .validators.json_safe import parse_json_strict

BASE = Path(__file__).resolve().parent
PROMPTS = BASE / "prompts"

def _render(template: str, **kwargs) -> str:
    out = template
    for k, v in kwargs.items():
        out = out.replace("{{" + k + "}}", v)
    return out

def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)

def run_multi_agent_pipeline(cv_profile: Dict[str, Any], job_post: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    """Optional Multi-Agent Pipeline (sequential, LiteLLM).

    Returns dict with at least:
      - body_text (clean body-only text)
      - issues (review issues)
      - open_questions
      - do_not_claim
      - top_fit_points
    """

    # 1) Extractor
    extractor_tpl = (PROMPTS / "extractor.md").read_text(encoding="utf-8")
    extractor_prompt = _render(extractor_tpl, CV_PROFILE_JSON=_j(cv_profile), JOB_POST_JSON=_j(job_post))
    extractor_out = single_call_body_only(
        messages=[{"role":"system","content":"Return JSON only."},{"role":"user","content": extractor_prompt}],
        model=model,
        temperature=0.1,
        max_tokens=700,
    )
    ex = parse_json_strict(extractor_out)
    key_facts = ex.get("key_facts", [])
    gaps = ex.get("gaps_or_unknowns", [])
    do_not_claim = ex.get("do_not_claim", [])

    # 2) Matcher
    matcher_tpl = (PROMPTS / "matcher.md").read_text(encoding="utf-8")
    matcher_prompt = _render(matcher_tpl, KEY_FACTS_JSON=_j(key_facts), JOB_POST_JSON=_j(job_post))
    matcher_out = single_call_body_only(
        messages=[{"role":"system","content":"Return JSON only."},{"role":"user","content": matcher_prompt}],
        model=model,
        temperature=0.2,
        max_tokens=700,
    )
    ma = parse_json_strict(matcher_out)
    top_fit_points = ma.get("top_fit_points", [])
    safe_strengths = ma.get("safe_strengths", [])
    missing_req = ma.get("missing_requirements", [])

    # 3) Writer (body-only)
    writer_tpl = (PROMPTS / "writer_body_only.md").read_text(encoding="utf-8")
    writer_prompt = _render(
        writer_tpl,
        TOP_FIT_POINTS_JSON=_j(top_fit_points),
        SAFE_STRENGTHS_JSON=_j(safe_strengths),
        GAPS_JSON=_j(gaps),
        JOB_POST_JSON=_j(job_post),
    )
    body = single_call_body_only(
        messages=[{"role":"system","content":"Return BODY text only."},{"role":"user","content": writer_prompt}],
        model=model,
        temperature=0.3,
        max_tokens=380,
    ).strip()

    # 4) Reviewer gate
    reviewer_tpl = (PROMPTS / "reviewer.md").read_text(encoding="utf-8")
    reviewer_prompt = _render(reviewer_tpl, BODY_TEXT=body)
    reviewer_out = single_call_body_only(
        messages=[{"role":"system","content":"Return JSON only."},{"role":"user","content": reviewer_prompt}],
        model=model,
        temperature=0.1,
        max_tokens=450,
    )
    rv = parse_json_strict(reviewer_out)
    body_clean = (rv.get("body_text_clean") or body).strip()
    issues = rv.get("issues_found", [])

    return {
        "body_text": body_clean,
        "issues": issues,
        "open_questions": gaps,
        "do_not_claim": do_not_claim,
        "top_fit_points": top_fit_points,
        "missing_requirements": missing_req,
    }
