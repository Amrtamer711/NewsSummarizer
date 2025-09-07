"""
Stock analysis utilities for fetching and formatting metrics.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from json_helpers import format_json_schema
from llm_core import call_openai, call_perplexity, call_gemini


def format_large_number(num: float) -> str:
    """Format large numbers with appropriate suffixes."""
    if num >= 1e9:
        return f"{num/1e9:.2f}B"
    elif num >= 1e6:
        return f"{num/1e6:.2f}M"
    elif num >= 1e3:
        return f"{num/1e3:.2f}K"
    else:
        return f"{num:.2f}"


def calculate_wow_change(hist_1w: pd.DataFrame, current_price: float) -> float:
    """Calculate week-over-week percentage change."""
    if len(hist_1w) >= 2:
        week_ago_price = hist_1w['Close'].iloc[0]
        return ((current_price - week_ago_price) / week_ago_price * 100) if week_ago_price > 0 else 0
    return 0


def get_52_week_range(hist_1y: pd.DataFrame, info: Dict[str, Any]) -> tuple:
    """Get 52-week high and low."""
    if len(hist_1y) > 0:
        return hist_1y['High'].max(), hist_1y['Low'].min()
    else:
        return info.get('fiftyTwoWeekHigh', 0), info.get('fiftyTwoWeekLow', 0)


def get_avg_volume(hist_1w: pd.DataFrame, info: Dict[str, Any]) -> float:
    """Get 7-day average volume."""
    if len(hist_1w) > 0:
        return hist_1w['Volume'].mean()
    return info.get('averageVolume', 0)


def fetch_basic_stock_data(ticker_symbol: str) -> Dict[str, Any]:
    """
    Fetch basic stock data from yfinance.
    Returns ticker, info, and history data.
    """
    print(f"     📈 Fetching yfinance data for {ticker_symbol}...", flush=True)
    ticker = yf.Ticker(ticker_symbol)
    
    print(f"     📊 Getting company info...", flush=True)
    info = ticker.info
    
    print(f"     📅 Fetching 1-year history...", flush=True)
    hist_1y = ticker.history(period="1y")
    
    print(f"     📅 Fetching 7-day history...", flush=True)
    hist_1w = ticker.history(period="7d")
    
    # Get current price
    current_price = info.get('currentPrice', 0)
    if current_price == 0 and len(hist_1w) > 0:
        current_price = hist_1w['Close'].iloc[-1]
    
    print(f"     ✅ Basic data fetched. Current price: ${current_price:.2f}", flush=True)
    
    return {
        'ticker': ticker,
        'info': info,
        'hist_1y': hist_1y,
        'hist_1w': hist_1w,
        'current_price': current_price
    }


def calculate_market_metrics(stock_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Calculate Section A: Market Performance metrics.
    """
    info = stock_data['info']
    hist_1y = stock_data['hist_1y']
    hist_1w = stock_data['hist_1w']
    current_price = stock_data['current_price']
    
    # Calculate metrics
    wow_change = calculate_wow_change(hist_1w, current_price)
    week_52_high, week_52_low = get_52_week_range(hist_1y, info)
    avg_volume_7d = get_avg_volume(hist_1w, info)
    
    # Extract fields
    beta = info.get('beta')
    dividend_yield = info.get('dividendYield')
    trailing_pe = info.get('trailingPE')
    enterprise_to_ebitda = info.get('enterpriseToEbitda')
    
    return {
        "Current Price": f" ${current_price:.2f}",
        "% Change WoW": f" {wow_change:+.2f}%",
        "52-Week High/Low": f" ${week_52_high:.2f} / ${week_52_low:.2f}",
        "Market Cap": f" {format_large_number(info.get('marketCap', 0))}",
        "Volume (7d avg)": f" {format_large_number(avg_volume_7d)}",
        "Beta": f" {beta:.2f}" if beta is not None else ' N/A',
        "Dividend Yield": f" {dividend_yield * 100:.2f}%" if dividend_yield is not None else ' N/A',
        "P/E Ratio": f" {trailing_pe:.2f}" if trailing_pe is not None else ' N/A',
        "EV/EBITDA": f" {enterprise_to_ebitda:.2f}" if enterprise_to_ebitda is not None else ' N/A'
    }


def calculate_financial_metrics(stock_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Calculate Section B: Key Financials metrics.
    """
    info = stock_data['info']
    
    revenue_ttm = info.get('totalRevenue', 0)
    ebitda = info.get('ebitda', 0)
    net_income = info.get('netIncomeToCommon', 0)
    ebitda_margin = (ebitda / revenue_ttm * 100) if revenue_ttm > 0 else 0
    
    return {
        "TTM Revenue": f" {format_large_number(revenue_ttm)}",
        "TTM EBITDA": f" {format_large_number(ebitda)}",
        "Net Profit": f" {format_large_number(net_income)}",
        "EBITDA Margin": f" {ebitda_margin:.1f}%",
        "Net Debt": f" {format_large_number(info.get('totalDebt', 0) - info.get('totalCash', 0))}",
        "Debt-to-Equity": f" {info.get('debtToEquity', 'N/A'):.2f}" if info.get('debtToEquity') else ' N/A',
        "Free Cash Flow": f" {format_large_number(info.get('freeCashflow', 0))}"
    }


def get_operational_metrics(company_name: str, ticker_symbol: str, llm_enabled: Dict[str, bool], llm_config: Dict[str, Any], clients: Dict[str, Any], logger: Optional[Callable] = None) -> Dict[str, str]:
    all_metrics: Dict[str, Dict[str, str]] = {}

    # Prompt
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    prompt = [
        {
            "role": "system",
            "content": (
                f"Today's date is {current_date}. You are a professional financial analyst researching operational metrics for {company_name} ({ticker_symbol}). "
                "Search online using real web sources for the most recent operational data. Focus on investor reports, presentations, and reliable financial sources. "
                f"Only use data from {current_year-1} or {current_year}."
            ),
        },
        {
            "role": "user",
            "content": (
                "Return a JSON object with: digital_inventory, occupancy_rate, media_assets, geographic_footprint, recent_ma. "
                "Use 'Not disclosed' when not available."
            ),
        },
    ]

    schema = format_json_schema(
        {
            "type": "object",
            "properties": {
                "digital_inventory": {"type": "string"},
                "occupancy_rate": {"type": "string"},
                "media_assets": {"type": "string"},
                "geographic_footprint": {"type": "string"},
                "recent_ma": {"type": "string"},
            },
            "required": [
                "digital_inventory",
                "occupancy_rate",
                "media_assets",
                "geographic_footprint",
                "recent_ma",
            ],
            "additionalProperties": False,
        },
        name="operational_metrics",
    )

    # OpenAI
    if llm_enabled.get("openai") and clients.get("openai"):
        try:
            data = call_openai(
                client=clients["openai"],
                messages=prompt,
                model=llm_config["openai_model"],
                tools=[{"type": "web_search_preview"}],
                json_schema=schema,
            )
            all_metrics["openai"] = data
        except Exception as e:
            if logger: logger(f"OpenAI operational metrics error: {e}")

    # Perplexity
    if llm_enabled.get("perplexity") and llm_config.get("perplexity_api_key"):
        try:
            data = call_perplexity(
                api_key=llm_config["perplexity_api_key"],
                messages=prompt,
                model=llm_config["perplexity_model"],
                json_schema=schema,
                timeout=30,
            )
            all_metrics["perplexity"] = data
        except Exception as e:
            if logger: logger(f"Perplexity operational metrics error: {e}")

    # Gemini
    if llm_enabled.get("gemini") and clients.get("gemini"):
        print(f"       🤖 Calling Gemini for operational data...", flush=True)
        try:
            json_instruction = (
                "\n\nRespond ONLY with a raw JSON object. DO NOT include markdown fences. Ensure valid JSON with keys: "
                "digital_inventory, occupancy_rate, media_assets, geographic_footprint, recent_ma."
            )
            data = call_gemini(
                client=clients["gemini"],
                messages=prompt,
                model=llm_config["gemini_model"],
                json_instruction=json_instruction,
            )
            all_metrics["gemini"] = data
            print(f"       ✅ Gemini returned operational data", flush=True)
        except Exception as e:
            print(f"       ❌ Gemini failed: {str(e)[:50]}...", flush=True)
            if logger: logger(f"Gemini operational metrics error: {e}")

    # Aggregate via OpenAI
    if all_metrics and llm_enabled.get("openai") and clients.get("openai"):
        try:
            agg_schema = format_json_schema(schema["schema"], name="aggregated_metrics")
            messages = [
                {
                    "role": "system",
                    "content": f"You are a financial analyst synthesizing operational data for {company_name}.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Here is operational data from multiple sources:\n{json.dumps(all_metrics, indent=2)}\n\n"
                        "Synthesize to single factual statements for each key; use 'Not disclosed' if unknown."
                    ),
                },
            ]
            data = call_openai(
                client=clients["openai"],
                messages=messages,
                model=llm_config["openai_model"],
                json_schema=agg_schema,
            )
            return data
        except Exception as e:
            if logger: logger(f"Aggregation error: {e}")

    # Fallback simple merge
    final = {
        "digital_inventory": "Not disclosed",
        "occupancy_rate": "Not disclosed",
        "media_assets": "Not disclosed",
        "geographic_footprint": "Not disclosed",
        "recent_ma": "Not disclosed",
    }
    for _, metrics in all_metrics.items():
        for k, v in metrics.items():
            if v and v != "Not disclosed" and final[k] == "Not disclosed":
                final[k] = v
    return final


def get_categorized_news(company_name: str, ticker_symbol: str, llm_enabled: Dict[str, bool], llm_config: Dict[str, Any], clients: Dict[str, Any], logger: Optional[Callable] = None) -> Dict[str, str]:
    all_news: Dict[str, Dict[str, str]] = {}
    today = datetime.now()
    start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    prompt = [
        {"role": "system", "content": (
            f"Today's date is {end}. You are a professional news analyst researching {company_name} ({ticker_symbol}). "
            "Search online using real web sources and categorize recent news. Include only news within the date range."
        )},
        {"role": "user", "content": (
            f"Search for news about {company_name} from {start} to {end}. Categorize into keys: "
            "earnings, strategic, leadership, regulatory, sentiment. For each, provide a brief summary or 'None'."
        )},
    ]

    schema = format_json_schema(
        {
            "type": "object",
            "properties": {
                "earnings": {"type": "string"},
                "strategic": {"type": "string"},
                "leadership": {"type": "string"},
                "regulatory": {"type": "string"},
                "sentiment": {"type": "string"},
            },
            "required": ["earnings", "strategic", "leadership", "regulatory", "sentiment"],
            "additionalProperties": False,
        },
        name="categorized_news",
    )

    # OpenAI
    if llm_enabled.get("openai") and clients.get("openai"):
        print(f"       📰 OpenAI categorizing {company_name} news...", flush=True)
        try:
            data = call_openai(
                client=clients["openai"],
                messages=prompt,
                model=llm_config["openai_model"],
                tools=[{"type": "web_search_preview"}],
                json_schema=schema,
            )
            all_news["openai"] = data
            print(f"       ✅ OpenAI categorized news ready", flush=True)
        except Exception as e:
            print(f"       ❌ OpenAI categorization failed: {str(e)[:50]}...", flush=True)
            if logger: logger(f"OpenAI categorized news error: {e}")

    # Perplexity
    if llm_enabled.get("perplexity") and llm_config.get("perplexity_api_key"):
        print(f"       📰 Perplexity categorizing {company_name} news...", flush=True)
        try:
            data = call_perplexity(
                api_key=llm_config["perplexity_api_key"],
                messages=prompt,
                model=llm_config["perplexity_model"],
                json_schema=schema,
                timeout=30,
            )
            all_news["perplexity"] = data
            print(f"       ✅ Perplexity categorized news ready", flush=True)
        except Exception as e:
            print(f"       ❌ Perplexity categorization failed: {str(e)[:50]}...", flush=True)
            if logger: logger(f"Perplexity categorized news error: {e}")

    # Gemini
    if llm_enabled.get("gemini") and clients.get("gemini"):
        try:
            json_instruction = (
                "\n\nRespond ONLY with a raw JSON object for keys: earnings, strategic, leadership, regulatory, sentiment."
            )
            data = call_gemini(
                client=clients["gemini"],
                messages=prompt,
                model=llm_config["gemini_model"],
                json_instruction=json_instruction,
            )
            all_news["gemini"] = data
        except Exception as e:
            if logger: logger(f"Gemini categorized news error: {e}")

    # Aggregate with OpenAI
    if all_news and llm_enabled.get("openai") and clients.get("openai"):
        try:
            agg_schema = format_json_schema(schema["schema"], name="aggregated_news")
            messages = [
                {
                    "role": "system",
                    "content": f"You are a news analyst synthesizing categorized news for {company_name}.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Here is categorized news from multiple sources:\n{json.dumps(all_news, indent=2)}\n\n"
                        "Synthesize into single comprehensive summaries for each category; use 'None' if no news."
                    ),
                },
            ]
            data = call_openai(
                client=clients["openai"],
                messages=messages,
                model=llm_config["openai_model"],
                json_schema=agg_schema,
            )
            return data
        except Exception as e:
            if logger: logger(f"Aggregation error: {e}")

    # Fallback simple merge
    final = {"earnings": "None", "strategic": "None", "leadership": "None", "regulatory": "None", "sentiment": "None"}
    for _, news in all_news.items():
        for k, v in news.items():
            if v and v != "None" and final[k] == "None":
                final[k] = v
    return final


def get_company_news_items(company_name: str, ticker_symbol: str, llm_enabled: Dict[str, bool], llm_config: Dict[str, Any], clients: Dict[str, Any], logger: Optional[Callable] = None, max_items: int = 3) -> List[Dict[str, str]]:
    today = datetime.now()
    start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    prompt = [
        {"role": "system", "content": (
            f"Today's date is {end}. You are a professional news analyst. Find the most relevant and recent news about {company_name} ({ticker_symbol}). "
            f"Only include news from {start} to {end}."
        )},
        {"role": "user", "content": (
            f"Return up to {max_items} items as a JSON array of objects with keys: title, publisher, link, date. "
            "Ensure links are accessible."
        )},
    ]

    items: List[Dict[str, str]] = []

    # OpenAI: object with items array
    if llm_enabled.get("openai") and clients.get("openai"):
        try:
            schema = format_json_schema(
                {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "publisher": {"type": "string"},
                                    "link": {"type": "string"},
                                    "date": {"type": "string"},
                                },
                                "required": ["title", "publisher", "link", "date"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["items"],
                    "additionalProperties": False,
                },
                name="company_news_items",
            )
            data = call_openai(
                client=clients["openai"],
                messages=prompt,
                model=llm_config["openai_model"],
                tools=[{"type": "web_search_preview"}],
                json_schema=schema,
            )
            items.extend(data.get("items", []))
        except Exception as e:
            if logger: logger(f"OpenAI company news error: {e}")

    # Perplexity: top-level array
    if llm_enabled.get("perplexity") and llm_config.get("perplexity_api_key"):
        try:
            schema_arr = format_json_schema(
                {"type": "array", "items": {"type": "object", "properties": {
                    "title": {"type": "string"}, "publisher": {"type": "string"}, "link": {"type": "string"}, "date": {"type": "string"}
                }, "required": ["title", "publisher", "link", "date"]}},
                name="company_news_items_list",
            )
            data = call_perplexity(
                api_key=llm_config["perplexity_api_key"],
                messages=prompt,
                model=llm_config["perplexity_model"],
                json_schema=schema_arr,
                timeout=30,
            )
            items.extend(data)
            print(f"       ✅ Perplexity found {len(data) if isinstance(data, list) else 0} news items", flush=True)
        except Exception as e:
            print(f"       ❌ Perplexity news failed: {str(e)[:50]}...", flush=True)
            if logger: logger(f"Perplexity company news error: {e}")

    # Gemini: array via instruction
    if llm_enabled.get("gemini") and clients.get("gemini"):
        print(f"       🗞️  Gemini searching for {company_name} news...", flush=True)
        try:
            json_instruction = (
                "\n\nRespond ONLY with a raw JSON array of objects. DO NOT include markdown fences. "
                "Each object MUST have keys: 'title', 'publisher', 'link', 'date'."
            )
            data = call_gemini(
                client=clients["gemini"],
                messages=prompt,
                model=llm_config["gemini_model"],
                json_instruction=json_instruction,
            )
            if isinstance(data, dict) and "items" in data:
                data = data["items"]
            if isinstance(data, list):
                items.extend(data)
                print(f"       ✅ Gemini found {len(data)} news items", flush=True)
            else:
                print(f"       ⚠️  Gemini returned unexpected format", flush=True)
        except Exception as e:
            print(f"       ❌ Gemini news failed: {str(e)[:50]}...", flush=True)
            if logger: logger(f"Gemini company news error: {e}")

    # Refine & select top using OpenAI
    if items and llm_enabled.get("openai") and clients.get("openai"):
        print(f"       🔄 Refining {len(items)} total news items with OpenAI...", flush=True)
        try:
            schema_ref = format_json_schema(
                {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "publisher": {"type": "string"},
                                    "link": {"type": "string"},
                                    "date": {"type": "string"},
                                },
                                "required": ["title", "publisher", "link", "date"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["items"],
                    "additionalProperties": False,
                },
                name="refined_company_news",
            )
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an assistant cleaning and selecting company news items. "
                        f"De-duplicate near-identical stories and select at most {max_items} most relevant for {company_name} ({ticker_symbol})."
                    ),
                },
                {"role": "user", "content": json.dumps({"items": items})},
            ]
            data = call_openai(
                client=clients["openai"],
                messages=messages,
                model=llm_config["openai_model"],
                json_schema=schema_ref,
            )
            items = data.get("items", [])[:max_items]
        except Exception as e:
            if logger: logger(f"Refine company news error: {e}")
            items = items[:max_items]
    else:
        items = items[:max_items]

    # Map to expected shape for HTML
    out: List[Dict[str, str]] = []
    for it in items:
        out.append({
            "title": it.get("title", ""),
            "publisher": it.get("publisher", ""),
            "link": it.get("link", ""),
        })
    return out


def get_analyst_signal(ticker: Any) -> str:
    """
    Get latest analyst recommendation.
    """
    try:
        recommendations = ticker.recommendations
        if recommendations is not None and len(recommendations) > 0:
            latest_rec = recommendations.iloc[-1]
            return f"Latest: {latest_rec.get('toGrade', 'N/A')} by {latest_rec.get('firm', 'N/A')}"
        return "No recent updates"
    except Exception:
        return "N/A"


def log_message(logger: Optional[Callable], message: str):
    """Helper to log messages."""
    if logger is not None:
        logger(message)
    else:
        print(message)