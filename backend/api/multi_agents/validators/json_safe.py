import json

def parse_json_strict(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        # strip fenced blocks
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)
