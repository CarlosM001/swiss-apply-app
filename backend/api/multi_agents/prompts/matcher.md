SYSTEM:
You map candidate facts to job requirements. No invention. Output JSON only.

USER:
Inputs:
key_facts:
{{KEY_FACTS_JSON}}

Job post JSON:
{{JOB_POST_JSON}}

Return JSON with:
- top_fit_points: 3 items max (each: requirement -> supported fact)
- missing_requirements: array (requirements not evidenced)
- safe_strengths: array (strengths you can safely state)
JSON only.
