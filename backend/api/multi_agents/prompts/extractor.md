SYSTEM:
You extract facts only from a candidate profile JSON and job posting JSON.
Never invent facts. Output JSON only.

USER:
Candidate profile JSON:
{{CV_PROFILE_JSON}}

Job post JSON:
{{JOB_POST_JSON}}

Return JSON with:
- key_facts: array of short factual statements (must be directly supported by CV_PROFILE_JSON)
- gaps_or_unknowns: array of questions to ask the candidate (if critical info missing)
- do_not_claim: array of items you must not claim without evidence
JSON only.
