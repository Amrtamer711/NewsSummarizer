"""
News API fetching utilities.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import concurrent.futures
from newsapi import NewsApiClient
from newsdataapi.newsdataapi_client import NewsDataApiClient
from json_helpers import format_json_schema
from llm_core import call_openai, call_perplexity, call_gemini
import json


def fetch_news_api_articles(newsapi_client: NewsApiClient, query: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    try:
        results = newsapi_client.get_everything(
            q=query,
            from_param=start_date,
            to=end_date,
            language="en",
            sort_by="relevancy",
            page_size=10,
        )
        articles = []
        for a in results.get("articles", []):
            articles.append({
                "title": a["title"],
                "summary": a.get("description", "") or "",
                "source": a["source"]["name"],
                "url": a["url"],
                "date": a["publishedAt"],
                "client": "NewsAPI",
            })
        return articles
    except Exception as e:
        return [{"title": "NewsAPI Error", "summary": str(e), "url": "", "source": "NewsAPI", "date": "", "client": "NewsAPI"}]


def fetch_newsdata_articles(newsdata_client: NewsDataApiClient, section: str, query: str) -> List[Dict[str, Any]]:
    try:
        results = newsdata_client.latest_api(q=query, language="en", country="ae" if "UAE" in section else None, page=0)
        items = []
        for a in results.get("results", [])[:5]:
            items.append({
                "title": a["title"],
                "summary": a.get("description", "") or "",
                "source": a.get("source_id", ""),
                "url": a.get("link", ""),
                "date": a.get("pubDate", ""),
                "client": "NewsDataAPI",
            })
        return items
    except Exception as e:
        return [{"title": "NewsDataAPI Error", "summary": str(e), "url": "", "source": "NewsDataAPI", "date": "", "client": "NewsDataAPI"}]


def fetch_news_from_multiple_apis(section: str, query: str, newsapi_client: Optional[NewsApiClient], newsdata_client: Optional[NewsDataApiClient], days_back: int = 3) -> List[Dict[str, Any]]:
    today = datetime.now()
    start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    collected: List[Dict[str, Any]] = []
    
    # Use concurrent execution like the original
    def _newsapi_call():
        if newsapi_client:
            collected.extend(fetch_news_api_articles(newsapi_client, query, start_date, end_date))
    
    def _newsdata_call():
        if newsdata_client:
            collected.extend(fetch_newsdata_articles(newsdata_client, section, query))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fut1 = ex.submit(_newsapi_call)
        fut2 = ex.submit(_newsdata_call)
        concurrent.futures.wait([fut1, fut2])
    
    return collected


def refine_articles(articles: List[Dict[str, Any]], section: str, openai_client: Any, model: str, max_articles: int) -> List[Dict[str, Any]]:
    if not articles:
        return []
    schema = format_json_schema({
        "type": "object",
        "properties": {
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "source": {"type": "string"},
                        "url": {"type": "string"},
                        "date": {"type": "string"}
                    },
                    "required": ["title", "summary", "source", "url", "date"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["articles"],
        "additionalProperties": False
    }, name="filtered_articles")

    messages = [
        {"role": "system", "content": (
            f"You are an assistant helping to clean and select news articles for the '{section}' section.\n\n"
            f"Your task is to:\n"
            f"1. Identify near-duplicate articles.\n"
            f"2. Keep only one version per unique story — the most credible.\n"
            f"3. Return at most {max_articles} relevant articles.\n\n"
            f"Return only the final selected articles in the same JSON format."
        )},
        {"role": "user", "content": f"Here are the articles for '{section}':\n\n" + json.dumps({"articles": articles})}
    ]

    data = call_openai(openai_client, messages, model, json_schema=schema)
    if isinstance(data, dict):
        return data.get("articles", [])[:max_articles]
    elif isinstance(data, list):
        return data[:max_articles]
    else:
        return []


def validate_and_fix_urls(articles: List[Dict[str, Any]], section: str, openai_client: Any, model: str, url_change_log: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if not articles:
        return []
    schema = format_json_schema({
        "type": "object",
        "properties": {
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "source": {"type": "string"},
                        "url": {"type": "string"},
                        "date": {"type": "string"}
                    },
                    "required": ["title", "summary", "source", "url", "date"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["articles"],
        "additionalProperties": False
    }, name="validated_articles")

    messages = [
        {"role": "system", "content": (
            f"You are an assistant validating and fixing URLs for the '{section}' section.\n"
            f"Replace broken or wrong URLs only when you are confident. Keep structure identical."
        )},
        {"role": "user", "content": f"Here are the articles for '{section}':\n\n" + json.dumps({"articles": articles})}
    ]

    data = call_openai(openai_client, messages, model, tools=[{"type": "web_search_preview"}], json_schema=schema)
    if isinstance(data, dict):
        fixed_list = data.get("articles", [])
    elif isinstance(data, list):
        fixed_list = data
    else:
        fixed_list = []
    
    # Track URL changes if log is provided
    if url_change_log is not None:
        for original, fixed in zip(articles, fixed_list):
            if original["url"].strip() != fixed["url"].strip():
                url_change_log.append({
                    "section": section,
                    "title": original["title"],
                    "old_url": original["url"],
                    "new_url": fixed["url"]
                })
    
    return fixed_list


def is_recent_article(article: Dict[str, Any], days: int = 7) -> bool:
    """
    Check if an article is within the specified number of days.
    """
    raw_date = article.get("date", "").strip()
    if not raw_date:
        return False
    
    try:
        date = datetime.fromisoformat(raw_date.replace("Z", "").split("T")[0])
        return (datetime.now() - date).days <= days
    except Exception:
        return False


def google_search_first_result(query: str) -> Optional[str]:
    """
    Resolve first search result link using SerpAPI. Falls back to HTML scrape if needed.
    """
    try:
        import requests
        import os
        from urllib.parse import quote, unquote
        from config import SERPAPI_KEY
        
        if SERPAPI_KEY:
            # 1) Try Google News via SerpAPI
            params_news = {
                "engine": "google_news",
                "q": query,
                "hl": "en",
                "gl": "us",
                "num": 10,
                "api_key": SERPAPI_KEY,
            }
            r = requests.get("https://serpapi.com/search", params=params_news, timeout=10)
            if r.ok:
                data = r.json()
                news_results = data.get("news_results") or []
                for item in news_results:
                    url = item.get("link") or item.get("source_url")
                    if url and url.startswith("http"):
                        return url
            
            # 2) Fallback to Google Organic via SerpAPI
            params_org = {
                "engine": "google",
                "q": query,
                "hl": "en",
                "gl": "us",
                "num": 10,
                "api_key": SERPAPI_KEY,
            }
            r2 = requests.get("https://serpapi.com/search", params=params_org, timeout=10)
            if r2.ok:
                data2 = r2.json()
                organic = data2.get("organic_results") or []
                if organic:
                    link = organic[0].get("link")
                    if link and link.startswith("http"):
                        return link
        
    except Exception as e:
        print(f"      SerpAPI error: {e}", flush=True)
    
    # Final fallback: existing HTML parsing approach
    try:
        import requests
        from urllib.parse import quote, unquote
        import re
        import html as ihtml
        
        search_url = f"https://www.google.com/search?q={quote(query)}"
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/115.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        html_text = ihtml.unescape(response.text)
        pattern_redirect_rel = r'href="/url\?q=([^"&]+)(?:&|&amp;)'  # relative
        pattern_redirect_abs = r'href="https?://www\.google\.com/url\?q=([^"&]+)(?:&|&amp;)'  # absolute
        for pattern in (pattern_redirect_rel, pattern_redirect_abs):
            import re
            matches = re.findall(pattern, html_text, flags=re.IGNORECASE)
            if matches:
                first_url = unquote(matches[0])
                if not first_url.startswith((
                    'http://www.google.', 'https://www.google.',
                    'http://google.', 'https://google.',
                    'https://accounts.', 'https://support.', 'https://policies.'
                )):
                    return first_url
        pattern_direct = r'<a[^>]+href="(https?://[^"#]+)"[^>]*>'
        for url in re.findall(pattern_direct, html_text, flags=re.IGNORECASE):
            if (not any(domain in url for domain in (
                'google.com', 'googleapis.com', 'gstatic.com', 'webcache.googleusercontent.com'
            )) and len(url) > 20 and '.' in url):
                return url
        return search_url
    except Exception as e:
        print(f"      Search/scraping error: {e}", flush=True)
        return None


def fix_article_urls_with_search(articles: List[Dict[str, Any]], llm_name: str) -> List[Dict[str, Any]]:
    """
    For each article, search Google for the title and replace URL with first result.
    """
    print(f"   🔍 Searching Google for {llm_name} article URLs...", flush=True)
    
    fixed_articles = []
    for idx, article in enumerate(articles, 1):
        title = article.get('title', '')
        source = article.get('source', '')
        original_url = article.get('url', '')
        
        # Construct search query
        search_query = f"{title} {source}"
        
        # Get first Google result
        found_url = google_search_first_result(search_query)
        
        if found_url:
            fixed_article = article.copy()
            fixed_article['url'] = found_url
            fixed_article['original_url'] = original_url
            fixed_articles.append(fixed_article)
            
            print(f"      {idx}. {title[:60]}...", flush=True)
            print(f"         Original: {original_url}", flush=True)
            
            # Check if we got an actual result or just the search URL
            if found_url.startswith("https://www.google.com/search"):
                print(f"         Fallback: {found_url} (couldn't extract first result)", flush=True)
            else:
                print(f"         ✓ Found: {found_url}", flush=True)
        else:
            # Keep original if search fails completely
            fixed_articles.append(article)
            print(f"      {idx}. ❌ Search failed, keeping original URL", flush=True)
    
    return fixed_articles


def fetch_llm_news_for_section(
    prompt: List[Dict[str, str]],
    llm_enabled: Dict[str, bool],
    llm_config: Dict[str, Any],
    clients: Dict[str, Any]
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []

    # OpenAI -> object with articles array; handle deep-research prompt variant
    if llm_enabled.get("openai") and clients.get("openai"):
        try:
            is_deep_research = "deep-research" in llm_config["openai_model"].lower()
            print(f"\n   📝 OpenAI Prompt:", flush=True)
            for msg in prompt:
                print(f"      [{msg['role'].upper()}]:", flush=True)
                print(f"      {msg['content']}", flush=True)
                print(f"      " + "-"*80, flush=True)
            if is_deep_research:
                modified_prompt = list(prompt)
                modified = dict(modified_prompt[-1])
                modified["content"] += (
                    "\n\nIMPORTANT: Return your response as a valid JSON object with the following structure:\n"
                    "{\n"
                    '  "articles": [\n'
                    "    {\n"
                    '      "title": "Article title",\n'
                    '      "summary": "2-4 sentence summary",\n'
                    '      "source": "Publication or website name",\n'
                    '      "url": "https://...",\n'
                    '      "date": "YYYY-MM-DD"\n'
                    "    },\n"
                    "    ... (repeat for all articles)\n"
                    "  ]\n"
                    "}\n\n"
                    "Ensure the response is valid JSON that can be parsed."
                )
                modified_prompt[-1] = modified
                print(f"\n   📝 OpenAI Deep-Research Modified User Prompt:", flush=True)
                print(f"      {modified['content']}", flush=True)
                print(f"      " + "-"*80, flush=True)
                data = call_openai(
                    client=clients["openai"],
                    messages=modified_prompt,
                    model=llm_config["openai_model"],
                    tools=[{"type": "web_search_preview"}],
                    json_schema=None,
                )
                if llm_config.get("test_mode"):
                    print(f"🔍 FINAL OUTPUT: {data}", flush=True)
                articles = data.get("articles", []) if isinstance(data, dict) else []
            else:
                schema_obj = format_json_schema({
                    "type": "object",
                    "properties": {
                        "articles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "summary": {"type": "string"},
                                    "source": {"type": "string"},
                                    "url": {"type": "string"},
                                    "date": {"type": "string"}
                                },
                                "required": ["title", "summary", "source", "url", "date"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["articles"],
                    "additionalProperties": False
                }, name="ai_news_response")
                data = call_openai(
                    client=clients["openai"],
                    messages=prompt,
                    model=llm_config["openai_model"],
                    tools=[{"type": "web_search_preview"}],
                    json_schema=schema_obj,
                )
                articles = data.get("articles", []) if isinstance(data, dict) else []
            for a in articles:
                a["client"] = "OpenAI"
            
            # Fix URLs with Google search before adding to collected
            articles = fix_article_urls_with_search(articles, "OpenAI")
            
            collected.extend(articles)
            print(f"   ✅ OpenAI ({llm_config['openai_model']}): {len(articles)} articles", flush=True)
            for idx, article in enumerate(articles, 1):
                print(f"      {idx}. {article.get('title', '')[:80]}...", flush=True)
                print(f"         Source: {article.get('source', '')} | Date: {article.get('date', '')}", flush=True)
                print(f"         URL: {article.get('url', '')}", flush=True)
        except Exception as e:
            print(f"   ❌ OpenAI ({llm_config['openai_model']}): ERROR - {str(e)}", flush=True)
            if llm_config.get("test_mode"):
                import traceback
                traceback.print_exc()

    # Perplexity -> top-level array
    if llm_enabled.get("perplexity") and llm_config.get("perplexity_api_key"):
        try:
            print(f"\n   📝 Perplexity Prompt:", flush=True)
            for msg in prompt:
                print(f"      [{msg['role'].upper()}]:", flush=True)
                print(f"      {msg['content']}", flush=True)
                print(f"      " + "-"*80, flush=True)
            schema_arr = format_json_schema({
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "source": {"type": "string"},
                        "url": {"type": "string"},
                        "date": {"type": "string"}
                    },
                    "required": ["title", "summary", "source", "url", "date"]
                }
            }, name="ai_news_list")
            items = call_perplexity(
                api_key=llm_config["perplexity_api_key"],
                messages=prompt,
                model=llm_config["perplexity_model"],
                json_schema=schema_arr,
                timeout=30
            )
            for a in items or []:
                a["client"] = "Perplexity"
            
            # Fix URLs with Google search before adding to collected
            if items:
                items = fix_article_urls_with_search(items, "Perplexity")
            
            collected.extend(items or [])
            print(f"   ✅ Perplexity ({llm_config['perplexity_model']}): {len(items or [])} articles", flush=True)
            for idx, article in enumerate(items if items else [], 1):
                print(f"      {idx}. {article.get('title', '')[:80]}...", flush=True)
                print(f"         Source: {article.get('source', '')} | Date: {article.get('date', '')}", flush=True)
                print(f"         URL: {article.get('url', '')}", flush=True)
        except Exception as e:
            print(f"   ❌ Perplexity ({llm_config['perplexity_model']}): ERROR - {str(e)}", flush=True)
            if llm_config.get("test_mode"):
                import traceback
                traceback.print_exc()

    # Gemini -> array via JSON instruction; adjust to EXACTLY 10 and no wrapping
    if llm_enabled.get("gemini") and clients.get("gemini"):
        try:
            print(f"\n   📝 Gemini Prompt (before modification):", flush=True)
            for msg in prompt:
                print(f"      [{msg['role'].upper()}]:", flush=True)
                print(f"      {msg['content']}", flush=True)
                print(f"      " + "-"*80, flush=True)
            modified_prompt = list(prompt)
            if len(modified_prompt) > 1 and "content" in modified_prompt[1]:
                modified_prompt[1]["content"] = modified_prompt[1]["content"].replace(
                    "exactly 5",
                    "exactly 10"
                )
            json_instruction = (
                "\n\nRespond ONLY with a raw JSON array of objects. "
                "DO NOT wrap the array in a dictionary like {\"articles\": [...]}. "
                "DO NOT include markdown formatting such as ```json. "
                "Each object MUST contain exactly these keys: 'title', 'summary', 'source', 'url', 'date'. "
                "Remember to return EXACTLY 10 articles, not 5. "
                "Ensure it is valid JSON and parsable by Python's json.loads()."
            )
            print(f"\n   📝 Gemini Modified User Prompt (with JSON instruction):", flush=True)
            print(f"      {modified_prompt[1]['content'] + json_instruction}", flush=True)
            print(f"      " + "-"*80, flush=True)
            parsed = call_gemini(
                client=clients["gemini"],
                messages=modified_prompt,
                model=llm_config["gemini_model"],
                json_instruction=json_instruction
            )
            if isinstance(parsed, dict) and "articles" in parsed:
                parsed = parsed["articles"]
            if isinstance(parsed, list):
                for a in parsed:
                    a["client"] = "Gemini"
                
                # Fix URLs with Google search before adding to collected
                parsed = fix_article_urls_with_search(parsed, "Gemini")
                
                collected.extend(parsed)
                print(f"   ✅ Gemini ({llm_config['gemini_model']}): {len(parsed)} articles", flush=True)
                for idx, article in enumerate(parsed, 1):
                    print(f"      {idx}. {article.get('title', '')[:80]}...", flush=True)
                    print(f"         Source: {article.get('source', '')} | Date: {article.get('date', '')}", flush=True)
                    print(f"         URL: {article.get('url', '')}", flush=True)
        except Exception as e:
            print(f"   ❌ Gemini ({llm_config['gemini_model']}): ERROR - {str(e)}", flush=True)
            if llm_config.get("test_mode"):
                import traceback
                traceback.print_exc()

    return collected