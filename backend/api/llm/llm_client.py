from __future__ import annotations
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from litellm import completion

DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.25"))
DEFAULT_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "420"))

MIN_WORDS = int(os.getenv("LETTER_MIN_WORDS", "150"))
MAX_WORDS = int(os.getenv("LETTER_MAX_WORDS", "240"))

@dataclass
class LLMResult:
    body_text: str
    model: str
    usage: Dict[str, Any]

class LLMError(RuntimeError):
    pass

def generate_cover_letter_body_only(
    *,
    prompt: str,
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> LLMResult:
    chosen_model = model or DEFAULT_LLM_MODEL

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are a Swiss de-CH cover-letter writer. "
                "Return ONLY the BODY text. No header lines, no subject line, "
                "no date/place, no recipient block, no closing line, no signature. "
                "No bullet lists. 2–3 paragraphs. 150–240 words. "
                "Never invent facts. Do not mention AI."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        resp = completion(
            model=chosen_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        raise LLMError(f"LLM call failed: {e}") from e

    try:
        text = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage", {}) or {}
    except Exception as e:
        raise LLMError(f"Unexpected LLM response format: {e}") from e

    cleaned = sanitize_body_only(text)
    cleaned = enforce_word_range(cleaned, MIN_WORDS, MAX_WORDS)

    return LLMResult(body_text=cleaned, model=chosen_model, usage=usage)

_HEADER_LIKE_PATTERNS = [
    r"^\s*bewerbung\s+als\s+.+$",
    r"^\s*betreff\s*:.*$",
    r"^\s*\d{1,2}\.\d{1,2}\.\d{2,4}\s*$",
    r"^\s*[A-ZÄÖÜ][\wÄÖÜäöüß\s\-]+,\s*\d{1,2}\.\d{1,2}\.\d{2,4}\s*$",
    r"^\s*freundliche\s+gr(ü|ue)sse.*$",
    r"^\s*mit\s+freundlichen\s+gr(ü|ue)sse.*$",
    r"^\s*sehr\s+geehrte.*$",
    r"^\s*guten\s+tag.*$"
]

def sanitize_body_only(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()

    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"^[\s•\-\–\*]+\s+", "", t, flags=re.MULTILINE)

    lines = [ln.strip() for ln in t.split("\n")]
    filtered: List[str] = []
    for ln in lines:
        if not ln:
            filtered.append("") 
            continue
        lower_ln = ln.lower()
        if any(re.match(pat, lower_ln, flags=re.IGNORECASE) for pat in _HEADER_LIKE_PATTERNS):
            continue
        filtered.append(ln)

    rebuilt = "\n".join(filtered)
    rebuilt = re.sub(r"\n{3,}", "\n\n", rebuilt).strip()

    paras = [p.strip() for p in rebuilt.split("\n\n") if p.strip()]
    if len(paras) > 3:
        head = paras[:2]
        tail = " ".join(paras[2:])
        paras = head + [tail.strip()]
    rebuilt = "\n\n".join(paras).strip()

    return rebuilt

def enforce_word_range(body: str, min_words: int, max_words: int) -> str:
    words = re.findall(r"\S+", body)
    if len(words) <= max_words:
        return body
    sentences = re.split(r"(?<=[\.\!\?])\s+", body.strip())
    out = []
    count = 0
    for s in sentences:
        w = re.findall(r"\S+", s)
        if count + len(w) <= max_words:
            out.append(s)
            count += len(w)
        else:
            break
    if out:
        return " ".join(out).strip()
    return " ".join(words[:max_words]).strip()