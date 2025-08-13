"""
JSON extraction and parsing utilities.
"""

import json
import re
from typing import Any, Dict, Optional


def extract_json_from_text(text: str) -> str:
    if not text:
        return ""
    if "```json" in text:
        start = text.find("```json") + len("```json")
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + len("```")
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    # Try to extract JSON array or object
    array_match = re.search(r"\[\s*{.*?}\s*\]", text, re.DOTALL)
    if array_match:
        return array_match.group(0)
    object_match = re.search(r"\{\s*\".*?\"\s*:.*?\}", text, re.DOTALL)
    if object_match:
        return object_match.group(0)
    return text.strip()


def safe_json_parse(text: str, default: Any = None) -> Any:
    try:
        cleaned = extract_json_from_text(text)
        return json.loads(cleaned)
    except Exception:
        return default


def format_json_schema(schema: Dict[str, Any], name: str = "response", strict: bool = True) -> Dict[str, Any]:
    return {
        "name": name,
        "schema": schema,
        "strict": strict
    }