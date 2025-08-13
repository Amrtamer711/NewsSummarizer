import os
from datetime import datetime
import smtplib
import yfinance as yf
import matplotlib.pyplot as plt
import mplcyberpunk
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from newsapi import NewsApiClient
from newsdataapi.newsdataapi_client import NewsDataApiClient
from config import APP_PSWD, NEWS_API_KEY, NEWS_IO_KEY, PERPLEXITY_API_KEY
import requests
import json
from prompts import uae_ooh_prompt, global_ooh_prompt, uae_marketing_prompt, global_marketing_prompt, uae_business_prompt, global_business_prompt
from clients import client, gemini_client
newsapi_client = NewsApiClient(api_key=NEWS_API_KEY)
newsdata_client = NewsDataApiClient(apikey=NEWS_IO_KEY)
from datetime import timedelta
from google.genai import types
import re
from urllib.parse import quote
from stock_metrics import get_comprehensive_stock_metrics, format_metrics_html, generate_stock_summary_table
import concurrent.futures
import contextlib
import io

STOCKS = [
    {"name": "JCDecaux SE", "ticker": "DEC.PA"},
    {"name": "Clear Channel Outdoor", "ticker": "CCO"},
    {"name": "Lamar Advertising", "ticker": "LAMR"},
    {"name": "Outfront Media", "ticker": "OUT"},
    {"name": "Ströer SE", "ticker": "SAX.DE"},
    {"name": "APG SGA", "ticker": "APGN.SW"},
    {"name": "oOh!media Limited", "ticker": "OML.AX"},
    {"name": "Focus Media Information Tech", "ticker": "002027.SZ"}, # Only if data is available!
]

MODEL_CONFIG = {
    "openai_model": "gpt-5", # "o4-mini-deep-research",
    "perplexity_model": "sonar-pro",
    "gemini_model": "gemini-2.5-pro"
}

# LLM Selection - Set to True/False to enable/disable each LLM
LLM_ENABLED = {
    "openai": True,      # OpenAI (GPT-5) - Disabled due to hallucinations
    "perplexity": True,   # Perplexity (Sonar Pro)
    "gemini": True        # Google Gemini
}

TEST_MODE = True

SECTION_ORDER = [
    "UAE OOH",
    "UAE Marketing",
    "UAE Business",
    "Global OOH",
    "Global Marketing",
    "Global Business",
]

MAX_ARTICLES_PER_SECTION = 6

def is_recent_article(article, days=7):
    raw_date = article.get("date", "").strip()
    if not raw_date:
        return False  # Reject if missing or empty

    try:
        # Try multiple formats, fallback if time component is present
        date = datetime.fromisoformat(raw_date.replace("Z", "").split("T")[0])
        return (datetime.now() - date).days <= days
    except Exception:
        return False  # Reject if unparseable

def extract_possible_json(raw_output):
    # Remove markdown code fences if present
    if "```json" in raw_output:
        start = raw_output.find("```json") + len("```json")
        end = raw_output.find("```", start)
        return raw_output[start:end].strip()
    
    # Try to extract JSON array using regex
    array_match = re.search(r"\[\s*{.*?}\s*\]", raw_output, re.DOTALL)
    if array_match:
        return array_match.group(0)

    return raw_output.strip()

# === CONFIG ===
FROM_EMAIL = "daily.multiply.news@gmail.com"
TO_EMAIL = "atmh2002@gmail.com"
# Update subject based on day of week
is_monday_check = datetime.now().weekday() == 0
SUBJECT = "📊 Weekly Digest – Stock + News" if is_monday_check else "📰 Daily News Digest"
DATE_STR = datetime.now().strftime("%B %d, %Y")

# === STOCK GRAPH ===
def plot_stock_chart(ticker, name=None, period="7d"):
    """Plot stock chart for specified period (default 7 days for weekly tracking)"""
    data = yf.Ticker(ticker).history(period=period)
    plt.style.use("cyberpunk")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(data.index, data["Close"], label=f"{name or ticker} Closing Price", linewidth=2.2)
    
    # Calculate percentage change
    if len(data) > 0:
        start_price = data["Close"].iloc[0]
        end_price = data["Close"].iloc[-1]
        pct_change = ((end_price - start_price) / start_price) * 100
        period_text = "7-Day" if period == "7d" else period.upper()
        ax.set_title(f"{name or ticker} – {period_text} Trend ({pct_change:+.2f}%)", fontsize=14)
    else:
        ax.set_title(f"{name or ticker} – {period.upper()} Trend", fontsize=14)
    
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (Local)")
    ax.legend()
    mplcyberpunk.add_glow_effects()
    path = f"{ticker}_{period}.png"
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()
    return path

# === FETCH AI NEWS ===
def fetch_ai_news():
    prompt_map = {
        "UAE OOH": uae_ooh_prompt,
        "Global OOH": global_ooh_prompt,
        "UAE Marketing": uae_marketing_prompt,
        "Global Marketing": global_marketing_prompt,
        "UAE Business": uae_business_prompt,
        "Global Business": global_business_prompt
    }

    sections = list(prompt_map.keys())
    all_section_articles = {}
    
    def _process_section(key: str):
        prompt = prompt_map[key]
        collected = []
        # OpenAI
        if LLM_ENABLED["openai"]:
            try:
                is_deep_research = "deep-research" in MODEL_CONFIG["openai_model"].lower()
                background = False
                if is_deep_research:
                    modified_prompt = prompt.copy()
                    modified_prompt[-1]["content"] += (
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

                    response = client.responses.create(
                        model=MODEL_CONFIG["openai_model"],
                        input=modified_prompt,
                        tools=[{"type": "web_search_preview"}],
                        background=background
                    )
                    final_output = response.output_text
                    print(f"🔍 FINAL OUTPUT: {final_output}", flush=True)
                else:
                    response = client.responses.create(
                        model=MODEL_CONFIG["openai_model"],
                        input=prompt,
                        tools=[{"type": "web_search_preview"}],
                        background=background,
                        text={
                            "format": {
                                "type": "json_schema",
                                "name": "ai_news_response",
                                "schema": {
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
                                },
                                "strict": True
                            }
                        },
                        reasoning={"effort": "low"}
                    )

                try:
                    if is_deep_research:
                        raw_text = final_output if 'final_output' in locals() else response.output_text
                    else:
                        raw_text = response.output_text

                    if "```json" in raw_text:
                        start = raw_text.find("```json") + len("```json")
                        end = raw_text.find("```", start)
                        json_text = raw_text[start:end].strip()
                    elif "```" in raw_text:
                        start = raw_text.find("```") + len("```")
                        end = raw_text.find("```", start)
                        json_text = raw_text[start:end].strip()
                    else:
                        json_text = raw_text.strip()

                    articles_data = json.loads(json_text).get("articles", [])
                except Exception as parse_error:
                    print(f"⚠️ Parse error: {parse_error}", flush=True)
                    articles_data = []

                print(f"\n✅ OpenAI ({MODEL_CONFIG['openai_model']}) - {key}: {len(articles_data)} articles", flush=True)
                if articles_data:
                    for idx, article in enumerate(articles_data, 1):
                        print(f"   {idx}. {article['title'][:80]}...", flush=True)
                        if TEST_MODE:
                            print(f"      Source: {article['source']} | Date: {article['date']}", flush=True)
                            print(f"      URL: {article.get('url','')}", flush=True)

                for article in articles_data:
                    article["client"] = "OpenAI"
                    collected.append(article)
            except Exception as e:
                print(f"\n❌ OpenAI ({MODEL_CONFIG['openai_model']}) - {key}: ERROR - {str(e)}", flush=True)
                if TEST_MODE:
                    import traceback
                    traceback.print_exc()

                collected.append({
                    "title": f"{key} (OpenAI) failed",
                    "url": "",
                    "summary": str(e),
                    "source": "OpenAI",
                    "date": "",
                    "client": "OpenAI"
                })

        # Perplexity
        if LLM_ENABLED["perplexity"]:
            try:
                r = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": MODEL_CONFIG["perplexity_model"],
                        "messages": prompt,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "schema": {
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
                                }
                            }
                        }
                    }, timeout=30
                )
                articles_data = json.loads(r.json()["choices"][0]["message"]["content"])

                print(f"\n✅ Perplexity ({MODEL_CONFIG['perplexity_model']}) - {key}: {len(articles_data)} articles", flush=True)
                if articles_data:
                    for idx, article in enumerate(articles_data, 1):
                        print(f"   {idx}. {article['title'][:80]}...", flush=True)
                        if TEST_MODE:
                            print(f"      Source: {article['source']} | Date: {article['date']}", flush=True)
                            print(f"      URL: {article.get('url','')}", flush=True)

                for article in articles_data:
                    article["client"] = "Perplexity"
                    collected.append(article)
            except Exception as e:
                print(f"\n❌ Perplexity ({MODEL_CONFIG['perplexity_model']}) - {key}: ERROR - {str(e)}", flush=True)
                if TEST_MODE:
                    import traceback
                    traceback.print_exc()

                collected.append({
                    "title": f"{key} (Perplexity) failed",
                    "url": "",
                    "summary": str(e),
                    "source": "Perplexity",
                    "date": "",
                    "client": "Perplexity"
                })

        # Gemini
        if LLM_ENABLED["gemini"]:
            try:
                response_schema = {
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
                }

                grounding_tool = types.Tool(google_search=types.GoogleSearch())

                modified_prompt = prompt.copy()
                modified_prompt[1]["content"] = modified_prompt[1]["content"].replace(
                    "You must return exactly 5 articles",
                    "You must return exactly 10 articles"
                )

                json_instruction = (
                    "\n\nRespond ONLY with a raw JSON array of objects. "
                    "DO NOT wrap the array in a dictionary like {\"articles\": [...]}. "
                    "DO NOT include markdown formatting such as ```json. "
                    "Each object MUST contain exactly these keys: 'title', 'summary', 'source', 'url', 'date'. "
                    "Remember to return EXACTLY 10 articles, not 5. "
                    "Ensure it is valid JSON and parsable by Python's json.loads()."
                )

                config = types.GenerateContentConfig(
                    system_instruction=modified_prompt[0]["content"],
                    tools=[grounding_tool]
                )

                gemini_resp = gemini_client.models.generate_content(
                    model=MODEL_CONFIG["gemini_model"],
                    contents=modified_prompt[1]["content"] + json_instruction,
                    config=config,
                )

                raw_output = gemini_resp.text.strip()
                extracted_json = extract_possible_json(raw_output)
                parsed = json.loads(extracted_json)
                if isinstance(parsed, dict) and "articles" in parsed:
                    parsed = parsed["articles"]
                if not isinstance(parsed, list):
                    raise ValueError(f"Parsed Gemini output is not a list: {parsed}")

                print(f"\n✅ Gemini ({MODEL_CONFIG['gemini_model']}) - {key}: {len(parsed)} articles", flush=True)
                if parsed:
                    for idx, article in enumerate(parsed, 1):
                        print(f"   {idx}. {article['title'][:80]}...", flush=True)
                        if TEST_MODE:
                            print(f"      Source: {article['source']} | Date: {article['date']}", flush=True)
                            print(f"      URL: {article.get('url','')}", flush=True)

                for article in parsed:
                    article["client"] = "Gemini"
                    collected.append(article)
            except Exception as e:
                print(f"\n❌ Gemini ({MODEL_CONFIG['gemini_model']}) - {key}: ERROR - {str(e)}", flush=True)
                if TEST_MODE:
                    import traceback
                    traceback.print_exc()

                collected.append({
                    "title": f"{key} (Gemini) failed",
                    "url": "",
                    "summary": str(e),
                    "source": "Gemini",
                    "date": "",
                    "client": "Gemini"
                })

        return key, collected

    for k in sections:
        sec, articles = _process_section(k)
        all_section_articles[sec] = articles

    return all_section_articles

# === FETCH NEWS API ARTICLES ===
def fetch_news():
    today = datetime.now()
    start_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    query_map = {
        "UAE OOH": "UAE out-of-home advertising OR UAE billboard OR UAE digital signage",
        "Global OOH": "global out-of-home advertising OR billboard OR digital signage",
        "UAE Marketing": "UAE marketing agency OR UAE digital marketing OR UAE ad agency",
        "Global Marketing": "global marketing agency OR digital marketing",
        "UAE Business": "UAE business OR UAE corporate OR UAE economy",
        "Global Business": "global business OR world economy OR international companies OR business"
    }

    sections = list(query_map.keys())
    all_section_articles = {}
    logs_by_section = {}

    def _process_section(section: str):
        query = query_map[section]
        buf = io.StringIO()
        collected = []
        with contextlib.redirect_stdout(buf):
            # Run NewsAPI and NewsDataAPI in parallel per section
            def _newsapi_call():
                try:
                    results = newsapi_client.get_everything(
                        q=query,
                        from_param=start_date,
                        to=end_date,
                        language="en",
                        sort_by="relevancy",
                        page_size=10
                    )
                    articles_list = results.get("articles", [])
                    if TEST_MODE and articles_list:
                        print(f"\n📰 NewsAPI - {section}: {len(articles_list)} articles", flush=True)
                        for idx, article in enumerate(articles_list[:3], 1):
                            print(f"   {idx}. {article['title'][:80]}...", flush=True)
                            print(f"      URL: {article.get('url','')}", flush=True)
                    for article in articles_list:
                        collected.append({
                            "title": article["title"],
                            "summary": article["description"] or "",
                            "source": article["source"]["name"],
                            "url": article["url"],
                            "date": article["publishedAt"],
                            "client": "NewsAPI"
                        })
                except Exception as e:
                    collected.append({
                        "title": f"{section} (NewsAPI) failed",
                        "url": "",
                        "summary": str(e),
                        "source": "NewsAPI",
                        "date": "",
                        "client": "NewsAPI"
                    })

            def _newsdata_call():
                try:
                    results = newsdata_client.latest_api(
                        q=query,
                        language="en",
                        country="ae" if "UAE" in query else None,
                        page=0
                    )
                    articles_list = results.get("results", [])[:5]
                    if TEST_MODE and articles_list:
                        print(f"\n📡 NewsDataAPI - {section}: {len(articles_list)} articles", flush=True)
                        for idx, article in enumerate(articles_list[:3], 1):
                            print(f"   {idx}. {article['title'][:80]}...", flush=True)
                            print(f"      URL: {article.get('link','')}", flush=True)
                    for article in articles_list:
                        collected.append({
                            "title": article["title"],
                            "summary": article["description"] or "",
                            "source": article["source_id"],
                            "url": article["link"],
                            "date": article["pubDate"],
                            "client": "NewsDataAPI"
                        })
                except Exception as e:
                    collected.append({
                        "title": f"{section} (NewsDataAPI) failed",
                        "url": "",
                        "summary": str(e),
                        "source": "NewsDataAPI",
                        "date": "",
                        "client": "NewsDataAPI"
                    })

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                fut1 = ex.submit(_newsapi_call)
                fut2 = ex.submit(_newsdata_call)
                concurrent.futures.wait([fut1, fut2])

        return section, collected, buf.getvalue()

    for s in sections:
        sec, articles, logs = _process_section(s)
        all_section_articles[sec] = articles
        if logs:
            print(logs)

    return all_section_articles

# === FINAL FILTER & SELECTION ===
def refine_articles_by_section(collected_articles_by_section):
    final_sections = {}

    for section, articles in collected_articles_by_section.items():
        try:
            response = client.responses.create(
                model=MODEL_CONFIG["openai_model"],
                input=[
                    {
                        "role": "system",
                        "content": (
                            f"You are an assistant helping to clean and select news articles for the '{section}' section.\n\n"
                            f"Your task is to:\n"
                            f"1. Identify near-duplicate articles (same story with slightly different wording).\n"
                            f"2. Keep only **one version per unique story** — preferably the most complete, informative, or credible.\n"
                            f"3. From the unique articles, return **at most 6 of the most relevant** ones for this section.\n\n"
                            f"If there are fewer than 6 good articles, return only those.\n\n"
                            f"Return only the final selected articles in the **exact same JSON format** you received."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Here are the articles for the '{section}' section:\n\n{json.dumps({'articles': articles})}"
                    }
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "filtered_articles",
                        "schema": {
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
                        },
                        "strict": True
                    }
                }
            )
            filtered = json.loads(response.output_text)
            # Enforce hard cap after model selection
            final_sections[section] = filtered["articles"][:MAX_ARTICLES_PER_SECTION]
        except Exception as e:
            final_sections[section] = [{
                "title": f"{section} (Filter Failed)",
                "url": "",
                "summary": str(e),
                "source": "OpenAI Final Filter",
                "date": ""
            }]

    return final_sections

def fix_article_urls_by_section(filtered_sections):
    fixed_sections = {}
    url_change_log = []

    for section, articles in filtered_sections.items():
        try:
            response = client.responses.create(
                model=MODEL_CONFIG["openai_model"],
                input=[
                    {
                        "role": "system",
                        "content": (
                            f"You are an assistant helping to validate and fix URLs of news articles in the '{section}' section.\n\n"
                            f"Your task is:\n"
                            f"1. Go through all articles provided.\n"
                            f"2. For each article, verify whether the 'url' field correctly leads to the actual article described by the title and summary.\n"
                            f"3. If the URL is clearly broken, wrong, or outdated — and you are confident — replace it with a working and correct one.\n"
                            f"4. If you are not confident, leave the original URL unchanged. Do NOT hallucinate URL changes. Only change when you are sure the link you found is correct and the one in the JSON is incorrect.\n"
                            f"5. Never remove or skip any articles.\n\n"
                            f"Return the exact same articles list with the updated 'url' fields.\n"
                            f"The output MUST follow the same JSON structure you received."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Here are the articles for the '{section}' section:\n\n{json.dumps({'articles': articles})}"
                    }
                ],
                tools=[{"type": "web_search_preview"}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "validated_articles",
                        "schema": {
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
                        },
                        "strict": True
                    }
                }
            )

            parsed = json.loads(response.output_text)
            fixed_list = parsed["articles"]
            fixed_sections[section] = fixed_list

            # 🔍 Log URL changes
            for original, fixed in zip(articles, fixed_list):
                if original["url"].strip() != fixed["url"].strip():
                    url_change_log.append({
                        "section": section,
                        "title": original["title"],
                        "old_url": original["url"],
                        "new_url": fixed["url"]
                    })

        except Exception as e:
            print(f"[URL Fix Failed] Section: {section} – {e}")
            fixed_sections[section] = [{
                "title": f"{section} (URL Fix Failed)",
                "url": "",
                "summary": str(e),
                "source": "OpenAI URL Fix",
                "date": ""
            }]

    # 📋 Print summary of changes
    print(f"\n🔧 URL Fix Summary: {len(url_change_log)} links updated\n")
    for change in url_change_log:
        print(f"🔗 [{change['section']}] {change['title']}\n→ OLD: {change['old_url']}\n→ NEW: {change['new_url']}\n")

    return fixed_sections

# === FORMAT HTML PER SECTION ===
def format_news_html_by_section(section_articles):
    html = ""
    for section in SECTION_ORDER:
        articles = section_articles.get(section, [])
        html += f"<h3 style='color:#fff;margin-top:30px;'>{section}</h3><ul style='padding-left:18px;'>"
        for item in articles:
            title = item.get("title", "Untitled")
            url = item.get("url", "#")
            desc = item.get("summary", "")
            desc_html = f"<p style='margin:4px 0 10px 0;color:#ccc;font-size:14px;'>{desc}</p>" if desc else ""
            html += f"<li style='margin-bottom:15px;'><a href='{url}' style='color:#4fc3f7;font-weight:bold;text-decoration:none;font-size:16px;'>{title}</a>{desc_html}</li>"
        html += "</ul>"
    return html

# === COMPOSE & SEND EMAIL ===
def build_and_send_email(test_mode=False):
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = SUBJECT

    print("🔍 Fetching AI-generated articles...")
    ai_articles = fetch_ai_news()
    if test_mode:
        for section, articles in ai_articles.items():
            print(f"  → {section}: {len(articles)} articles from AI")

    print("\n📰 Fetching direct news API articles...")
    news_articles = fetch_news()
    if test_mode:
        for section, articles in news_articles.items():
            print(f"  → {section}: {len(articles)} articles from News APIs")

    print("\n🧩 Merging sources...")
    merged_articles = {}
    for section in set(ai_articles.keys()).union(news_articles.keys()):
        merged = ai_articles.get(section, []) + news_articles.get(section, [])
        filtered_by_date = [a for a in merged if is_recent_article(a)]
        merged_articles[section] = filtered_by_date

    print("\n🧹 Refining and filtering merged articles...")
    filtered_articles = refine_articles_by_section(merged_articles)
    
    print("\n🔗 Validating article URLs...")
    if LLM_ENABLED.get("openai"):
        fixed_articles = fix_article_urls_by_section(filtered_articles)
    else:
        print("   Skipping URL validation (OpenAI disabled)")
        fixed_articles = filtered_articles  # Skip URL fixing when OpenAI is disabled
    
    # Print summary in test mode
    if test_mode:
        print("\n📊 FINAL ARTICLE SUMMARY:")
        total_articles = 0
        for section, articles in fixed_articles.items():
            print(f"  → {section}: {len(articles)} articles")
            total_articles += len(articles)
        print(f"  → TOTAL: {total_articles} articles across all sections")
    else:
        # Original detailed output for non-test mode
        for section, articles in fixed_articles.items():
            print(f"\n✅ Final [{section}] ({len(articles)} articles)")
            for a in articles:
                print(json.dumps(a, indent=2))

    # Check if today is Monday (weekday 0) or test mode
    is_monday = datetime.now().weekday() == 0 or test_mode
    
    stock_metrics = []
    stock_imgs = []

    if is_monday:
        if test_mode:
            print("🧪 TEST MODE: Fetching comprehensive OOH stock metrics...")
        else:
            print("📈 It's Monday! Fetching comprehensive OOH stock metrics...")

        # Parallelize per-stock work with clean logging per task
        def _process_stock(stock):
            buf = io.StringIO()
            img_path = None
            metrics = None
            def _logger(message: str):
                try:
                    buf.write(message + "\n")
                except Exception:
                    pass
            with contextlib.redirect_stdout(buf):
                print(f"\n📊 Fetching metrics for {stock['name']} ({stock['ticker']})...")
                llm_clients = {
                    "gemini": gemini_client if LLM_ENABLED.get("gemini") else None,
                    "openai": client if LLM_ENABLED.get("openai") else None
                }
                llm_config_with_key = MODEL_CONFIG.copy()
                llm_config_with_key["perplexity_api_key"] = PERPLEXITY_API_KEY
                try:
                    metrics = get_comprehensive_stock_metrics(
                        stock["ticker"],
                        stock["name"],
                        llm_enabled=LLM_ENABLED,
                        llm_config=llm_config_with_key,
                        clients=llm_clients,
                        logger=_logger
                    )
                    if test_mode and metrics and 'error' not in metrics:
                        print(f"  ✓ Current Price: {metrics['section_a']['Current Price']}")
                        print(f"  ✓ Week Change: {metrics['section_a']['% Change WoW']}")
                        print(f"  ✓ Market Cap: {metrics['section_a']['Market Cap']}")
                        print(f"  ✓ P/E Ratio: {metrics['section_a']['P/E Ratio']}")
                        print(f"  ✓ Revenue: {metrics['section_b']['TTM Revenue']}")
                        print(f"  ✓ EBITDA Margin: {metrics['section_b']['EBITDA Margin']}")
                        if metrics.get('news'):
                            print(f"  ✓ Latest News: {metrics['news'][0]['title'][:60]}...")
                    elif test_mode and metrics and 'error' in metrics:
                        print(f"  ✗ ERROR: {metrics['error']}")
                except Exception as e:
                    metrics = {
                        'company': stock['name'],
                        'ticker': stock['ticker'],
                        'error': str(e),
                        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    print(f"  ✗ Error fetching metrics: {e}")

                # Chart generation
                try:
                    if test_mode:
                        print(f"  📈 Generating 7-day chart...")
                    img_path = plot_stock_chart(stock["ticker"], stock["name"])
                    if test_mode:
                        print(f"  ✓ Chart saved to: {img_path}")
                except Exception as e:
                    print(f"  ✗ Error generating chart: {e}")

            return {
                'ticker': stock['ticker'],
                'name': stock['name'],
                'metrics': metrics,
                'img_path': img_path,
                'log': buf.getvalue()
            }

        # Sequential stock processing
        for s in STOCKS:
            res = _process_stock(s)
            if res['metrics']:
                stock_metrics.append(res['metrics'])
            if res['img_path']:
                stock_imgs.append({
                    'name': res['name'],
                    'ticker': res['ticker'],
                    'img_path': res['img_path']
                })
            if res['log']:
                print(res['log'])
    else:
        print("📅 Not Monday - skipping stock analysis")


    html = f"""\
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #0a0a0a;
                color: #fff;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #111;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Main Header Section with Background -->
            <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:30px;margin-bottom:30px;text-align:center;">
                <h1 style="color:#4fc3f7;margin:0;font-size:36px;font-weight:600;">
                    📬 Your {'Weekly' if is_monday else 'Daily'} Digest
                </h1>
                <p style="color:#aaa;font-size:18px;margin:10px 0 0 0;">{DATE_STR}</p>
                <p style="color:#ccc;font-size:16px;margin:10px 0 0 0;">
                    {'Comprehensive OOH Media Stock Analysis & News' if is_monday else 'Latest News & Updates'}
                </p>
            </div>
    """
    
    # Add comprehensive stock metrics
    if is_monday and stock_metrics:
        # Add summary table first
        html += generate_stock_summary_table(stock_metrics)
        
        # Add detailed metrics with integrated charts
        html += format_metrics_html(stock_metrics, stock_imgs)


    # Add news section with proper styling
    html += """
        <div style="margin-top:40px;">
            <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:20px;margin-bottom:20px;">
                <h2 style="color:#4fc3f7;margin:0;font-size:28px;text-align:center;">📰 News Articles</h2>
            </div>
    """
    
    for section in SECTION_ORDER:
        articles = fixed_articles.get(section, [])
        html += f"""
        <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:20px;margin-bottom:20px;">
            <h3 style='color:#4fc3f7;margin-top:0;font-size:22px;padding-bottom:15px;border-bottom:1px solid #333;'>
                {section}
            </h3>
            <ul style='padding-left:0;list-style:none;margin-top:20px;'>"""
        if not articles:
            html += "<li style='color:#ccc;'>No news available for this section.</li>"
        else:
            for item in articles:
                title = item.get("title", "Untitled")
                url = item.get("url", "#")
                desc = item.get("summary", "")
                
                # Create Google Apps Script webhook URL for one-click save
                # This will save directly to Google Sheets without any form
                SCRIPT_URL = "https://script.google.com/a/macros/mmg.global/s/AKfycbzwaJAFqQ5BkK5DHGEmFrC965q1xxJ-UsdsWy5IS1DmTHqBYEvbO2VIogBf4sdGCs8nXw/exec"
                
                # Build save URL with all data
                save_url = f"{SCRIPT_URL}?"
                save_url += f"title={quote(title)}"
                save_url += f"&url={quote(url)}"
                save_url += f"&section={quote(section)}"
                save_url += f"&summary={quote(desc[:500])}"  # Limit summary length
                
                desc_html = f"<p style='margin:4px 0 10px 0;color:#ccc;font-size:14px;'>{desc}</p>" if desc else ""
                
                # Simple save button - one click saves and shows confirmation
                save_button = f'<a href="{save_url}" target="_blank" style="float:right;background:#4CAF50;color:white;padding:4px 8px;border-radius:4px;text-decoration:none;font-size:12px;margin-left:10px;">Save 📌</a>'
                
                html += f"""
                <li style='margin-bottom:15px;border-bottom:1px solid #333;padding-bottom:15px;'>
                    {save_button}
                    <a href='{url}' style='color:#4fc3f7;font-weight:bold;text-decoration:none;font-size:16px;display:block;margin-bottom:5px;'>
                        {title}
                    </a>
                    {desc_html}
                </li>"""
        html += """
            </ul>
        </div>
        """

    # Close news section and HTML
    html += """
        </div>
        <p style="margin-top:20px;color:#aaa;font-size:13px;text-align:center;">✅ Auto-generated by your digest bot</p>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    if is_monday and stock_imgs:
        for s in stock_imgs:
            cid = s['ticker'].replace('.', '').replace('-', '')
            with open(s['img_path'], "rb") as f:
                image = MIMEImage(f.read(), name=os.path.basename(s['img_path']))
                image.add_header("Content-ID", f"<{cid}>")
                msg.attach(image)


    print("📤 Sending email...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_EMAIL, APP_PSWD)
        server.send_message(msg)

    print(f"✅ Email sent successfully to {TO_EMAIL}")


# === RUN ===
if __name__ == "__main__":
    import sys
    
    # Test mode - set to True to always show stocks regardless of day
    
    
    # Show which LLMs are enabled
    enabled_llms = [name for name, enabled in LLM_ENABLED.items() if enabled]
    if enabled_llms:
        print(f"✅ Enabled LLMs: {', '.join(enabled_llms)}")
    
    build_and_send_email(test_mode=TEST_MODE)
