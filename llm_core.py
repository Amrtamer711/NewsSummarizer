"""
Core LLM API call mechanics - handles the low-level API interactions.
The main scripts will handle prompt modifications and then call these functions.
"""

import json
import requests
from typing import Any, Dict, List, Optional
from google.genai import types
from json_helpers import extract_json_from_text


def call_openai(
    client: Any,
    messages: List[Dict[str, str]],
    model: str,
    tools: Optional[List[Dict]] = None,
    json_schema: Optional[Dict] = None,
    background: bool = False,
    reasoning_effort: str = "low",
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "model": model,
        "input": messages,
        "background": background,
    }
    if tools:
        params["tools"] = tools
    if json_schema:
        params["text"] = {
            "format": {
                "type": "json_schema",
                "name": json_schema.get("name", "response"),
                "schema": json_schema["schema"],
                "strict": json_schema.get("strict", True),
            }
        }
        params["reasoning"] = {"effort": reasoning_effort}

    resp = client.responses.create(**params)
    text = resp.output_text
    data = json.loads(extract_json_from_text(text))
    return data


def call_perplexity(
    api_key: str,
    messages: List[Dict[str, str]],
    model: str,
    json_schema: Optional[Dict] = None,
    timeout: int = 30,
) -> Any:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if json_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"schema": json_schema["schema"]},
        }

    r = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def call_gemini(
    client: Any,
    messages: List[Dict[str, str]],
    model: str,
    tools: Optional[List] = None,
    json_instruction: Optional[str] = None,
) -> Any:
    if tools is None:
        tools = [types.Tool(google_search=types.GoogleSearch())]
    if json_instruction is None:
        json_instruction = (
            "\n\nRespond ONLY with a raw JSON object or array. "
            "DO NOT include markdown fences. Ensure valid JSON."
        )

    config = types.GenerateContentConfig(
        system_instruction=messages[0]["content"] if messages and messages[0]["role"] == "system" else None,
        tools=tools,
    )
    user_content = messages[1]["content"] if len(messages) > 1 else messages[0]["content"]

    resp = client.models.generate_content(
        model=model,
        contents=user_content + json_instruction,
        config=config,
    )
    return json.loads(extract_json_from_text(resp.text.strip()))