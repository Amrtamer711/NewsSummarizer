#!/usr/bin/env python3
"""
Debug script: Call Gemini with the same workflow (tools + system/user) and print the raw response.
This helps inspect whether the response object contains citation/source URLs.
"""
import os
from datetime import datetime, timedelta
import json
from typing import Any

from clients import gemini_client
from send_email import MODEL_CONFIG
from google.genai import types


def safe_to_dict(obj: Any) -> Any:
	"""Best-effort conversion of Google GenAI response objects to dict for printing."""
	try:
		# Some response objects may support .to_dict()
		return obj.to_dict()  # type: ignore[attr-defined]
	except Exception:
		try:
			return json.loads(json.dumps(obj, default=str))
		except Exception:
			return str(obj)


def find_citation_urls(resp) -> list[str]:
	urls: list[str] = []
	try:
		candidates = getattr(resp, "candidates", []) or []
		for cand in candidates:
			# Direct citations
			for cit in getattr(cand, "citations", []) or []:
				uri = getattr(cit, "uri", None) or getattr(cit, "source_uri", None)
				if uri and isinstance(uri, str):
					urls.append(uri)
			# Grounding metadata
			gm = getattr(cand, "grounding_metadata", None)
			if gm is not None:
				chunks = getattr(gm, "grounding_chunks", []) or []
				for ch in chunks:
					web = getattr(ch, "web", None)
					if web is not None:
						uri = getattr(web, "uri", None)
						if uri and isinstance(uri, str):
							urls.append(uri)
	except Exception:
		pass
	# De-duplicate
	seen = set()
	out: list[str] = []
	for u in urls:
		if u not in seen:
			seen.add(u)
			out.append(u)
	return out


def main():
	# Same pattern: tools + system instruction + user; JSON instruction added like current call
	system_msg = (
		"You are a professional daily news analyst for executives. "
		"Use web search to find real, verifiable, recent news."
	)
	# Narrow to today's date window
	today = datetime.now()
	start = (today - timedelta(days=2)).strftime("%Y-%m-%d")
	end = today.strftime("%Y-%m-%d")
	user_msg = (
		f"Task: Return real UAE OOH articles published between {start} and {end}. "
		"Include title, summary (2–4 sentences), source, url, date (YYYY-MM-DD)."
	)

	# Configure tools and config (Google Search tool enabled)
	tools = [types.Tool(google_search=types.GoogleSearch())]
	config = types.GenerateContentConfig(
		system_instruction=system_msg,
		tools=tools,
	)

	# Keep same model as in MODEL_CONFIG
	model = MODEL_CONFIG.get("gemini_model", "gemini-2.5-pro")

	# Append JSON instruction like current workflow (even though we won't parse it here)
	json_instruction = (
		"\n\nRespond ONLY with a raw JSON array of objects. "
		"Each object MUST contain exactly these keys: 'title', 'summary', 'source', 'url', 'date'. "
		"Ensure it is valid JSON and parsable by Python's json.loads()."
	)

	print(f"→ Calling Gemini model: {model}")
	resp = gemini_client.models.generate_content(
		model=model,
		contents=user_msg + json_instruction,
		config=config,
	)

	print("\n=== Raw Response (repr) ===")
	print(repr(resp))
	print("\n=== Response Text ===")
	try:
		print(getattr(resp, "text", "<no text attribute>"))
	except Exception:
		print("<error printing resp.text>")

	print("\n=== Response as dict (best-effort) ===")
	print(json.dumps(safe_to_dict(resp), indent=2))

	urls = find_citation_urls(resp)
	print("\n=== Citation/Source URLs (best-effort) ===")
	if urls:
		for i, u in enumerate(urls, 1):
			print(f"{i}. {u}")
	else:
		print("<none found>")


if __name__ == "__main__":
	main() 