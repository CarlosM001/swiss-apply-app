from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import re

@dataclass
class SwitchDecision:
    mode: str
    reasons: List[str]
    risk_score: int

def decide_mode(cv_profile: Dict[str, Any], job_post: Dict[str, Any]) -> SwitchDecision:
    reasons: List[str] = []
    risk = 0

    gaps_months = _estimate_max_gap_months(cv_profile)
    if gaps_months >= 12:
        risk += 25; reasons.append(f"CV-Lücke geschätzt >= {gaps_months} Monate")

    title = (job_post.get("title") or "").lower()
    senior_markers = ["leiter", "lead", "head", "manager", "senior", "director", "c-level", "geschäftsführer"]
    if any(m in title for m in senior_markers):
        risk += 20; reasons.append("Senior/Leadership Rolle")

    industry_text = " ".join((job_post.get("requirements", {}).get("keywords") or [])).lower()
    regulated = ["medizin", "pharma", "bank", "finanz", "versicherung", "luftfahrt", "aviation", "security", "sicherheit"]
    if any(k in industry_text for k in regulated):
        risk += 15; reasons.append("Regulierte/High-stakes Branche")

    if _low_evidence(cv_profile):
        risk += 20; reasons.append("Wenig Evidenz/Details im CV")

    job_langs = set([s.lower() for s in (job_post.get("swiss", {}).get("language_requirements") or [])])
    cv_langs = set([s.lower() for s in (cv_profile.get("languages") or [])])
    if job_langs and not job_langs.issubset(cv_langs):
        risk += 10; reasons.append("Sprachanforderungen nicht klar belegt")

    if risk >= 40:
        return SwitchDecision(mode="multi", reasons=reasons, risk_score=min(risk, 100))
    return SwitchDecision(mode="single", reasons=reasons, risk_score=min(risk, 100))

def _low_evidence(cv_profile: Dict[str, Any]) -> bool:
    exp = cv_profile.get("experience") or []
    if len(exp) == 0:
        return True
    bullets = sum(len((e.get("bullets") or [])) for e in exp)
    skills = len(cv_profile.get("skills") or [])
    return bullets < 6 or skills < 8

def _estimate_max_gap_months(cv_profile: Dict[str, Any]) -> int:
    exp = cv_profile.get("experience") or []
    dates = []
    for e in exp:
        s = (e.get("start") or "")
        en = (e.get("end") or "")
        s_m = _parse_ym(s)
        e_m = _parse_ym(en) if en and en != "present" else None
        if s_m: dates.append(("start", s_m))
        if e_m: dates.append(("end", e_m))
    if len(dates) < 2:
        return 0
    starts = sorted([d for t, d in dates if t == "start"])
    ends = sorted([d for t, d in dates if t == "end"])
    if not starts or not ends:
        return 0
    max_gap = 0
    for e in ends:
        nxt = next((s for s in starts if s > e), None)
        if nxt:
            gap = nxt - e
            if gap > max_gap:
                max_gap = gap
    return max_gap

def _parse_ym(s: str):
    s = s.strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})(?:-(\d{1,2}))?$", s)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2) or 1)
    return year * 12 + month
