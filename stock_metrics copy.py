import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import json
import requests
from google.genai import types
import concurrent.futures

def _log(logger, message: str):
    if logger is not None:
        logger(message)
    else:
        print(message)

def fetch_operational_metrics(company_name, ticker_symbol, llm_enabled, llm_config, clients):
    """
    Fetch operational indicators for OOH companies using LLM web search
    Following the exact pattern as fetch_ai_news()
    """
    # Backwards compatibility wrapper: allow optional logger via kwargs
    logger = None
    if isinstance(llm_config, dict) and llm_config.get("__logger__"):
        logger = llm_config.get("__logger__")
    _log(logger, f"\n🔍 Fetching operational metrics for {company_name} ({ticker_symbol})...")
    
    # Get current date for context
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    
    # Create prompt in the same format as news prompts
    operational_prompt = [
        {
            "role": "system",
            "content": (
                f"Today's date is {current_date}. "
                f"You are a professional financial analyst researching operational metrics for {company_name} ({ticker_symbol}), "
                "an out-of-home advertising company. You must search online using real web sources and return the most recent "
                "operational data available. Focus on investor reports, company presentations, and reliable financial sources. "
                "Extract specific numeric values and operational indicators where available. "
                f"Only use data from {current_year-1} or {current_year}."
            )
        },
        {
            "role": "user", 
            "content": (
                f"Today is {current_date}. Search for and return the following operational metrics:\n"
                "1. % Digital Inventory - percentage of digital vs traditional displays\n"
                "2. Occupancy Rate - percentage of advertising inventory occupied/sold\n"
                "3. Number of Media Assets - total advertising panels/billboards/displays\n"
                "4. Geographic Footprint - countries/cities of operation\n"
                "5. Recent M&A / Divestments - acquisitions, mergers, or sales in last 12 months\n\n"
                "Return as JSON object with keys: digital_inventory, occupancy_rate, media_assets, geographic_footprint, recent_ma\n"
                "If data not available, use 'Not disclosed' as value."
            )
        }
    ]
    
    all_metrics = {}
    
    # OpenAI
    if llm_enabled.get("openai") and clients.get("openai"):
        try:
            is_deep_research = "deep-research" in llm_config["openai_model"].lower()
            background = False
            
            if is_deep_research:
                modified_prompt = operational_prompt.copy()
                modified_prompt[-1]["content"] += (
                    "\n\nIMPORTANT: Return your response as a valid JSON object with exactly these keys:\n"
                    "{\n"
                    '  "digital_inventory": "percentage or Not disclosed",\n'
                    '  "occupancy_rate": "percentage or Not disclosed",\n'
                    '  "media_assets": "number or Not disclosed",\n'
                    '  "geographic_footprint": "countries/cities or Not disclosed",\n'
                    '  "recent_ma": "description or Not disclosed"\n'
                    "}\n\n"
                    "Ensure the response is valid JSON that can be parsed."
                )
                
                response = clients["openai"].responses.create(
                    model=llm_config["openai_model"],
                    input=modified_prompt,
                    tools=[{"type": "web_search_preview"}],
                    background=background
                )
                response_text = response.output_text
            else:
                response = clients["openai"].responses.create(
                    model=llm_config["openai_model"],
                    input=operational_prompt,
                    tools=[{"type": "web_search_preview"}],
                    background=background,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "operational_metrics",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "digital_inventory": {"type": "string"},
                                    "occupancy_rate": {"type": "string"},
                                    "media_assets": {"type": "string"},
                                    "geographic_footprint": {"type": "string"},
                                    "recent_ma": {"type": "string"}
                                },
                                "required": ["digital_inventory", "occupancy_rate", "media_assets", "geographic_footprint", "recent_ma"],
                                "additionalProperties": False
                            },
                            "strict": True
                        }
                    }, 
                    reasoning={"effort": "low"}
                )
                response_text = response.output_text
            
            # Parse response
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text.strip()
            
            metrics_data = json.loads(json_text)
            all_metrics["openai"] = metrics_data
            
            # Print results summary
            _log(logger, f"\n✅ OpenAI ({llm_config['openai_model']}) - Operational Metrics for {company_name}:")
            for key, value in metrics_data.items():
                _log(logger, f"   • {key.replace('_', ' ').title()}: {value}")
                
        except Exception as e:
            _log(logger, f"\n❌ OpenAI ({llm_config['openai_model']}) - Operational Metrics for {company_name}: ERROR - {str(e)}")
    
    # Perplexity
    if llm_enabled.get("perplexity"):
        try:
            r = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {llm_config.get('perplexity_api_key', '')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": llm_config["perplexity_model"],
                    "messages": operational_prompt,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "digital_inventory": {"type": "string"},
                                    "occupancy_rate": {"type": "string"},
                                    "media_assets": {"type": "string"},
                                    "geographic_footprint": {"type": "string"},
                                    "recent_ma": {"type": "string"}
                                },
                                "required": ["digital_inventory", "occupancy_rate", "media_assets", "geographic_footprint", "recent_ma"]
                            }
                        }
                    }
                }
            )
            metrics_data = json.loads(r.json()["choices"][0]["message"]["content"])
            all_metrics["perplexity"] = metrics_data
            
            # Print results summary
            _log(logger, f"\n✅ Perplexity (sonar-pro) - Operational Metrics for {company_name}:")
            for key, value in metrics_data.items():
                _log(logger, f"   • {key.replace('_', ' ').title()}: {value}")
                
        except Exception as e:
            _log(logger, f"\n❌ Perplexity (sonar-pro) - Operational Metrics for {company_name}: ERROR - {str(e)}")
    
    # Gemini
    if llm_enabled.get("gemini") and clients.get("gemini"):
        try:
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            json_instruction = (
                "\n\nRespond ONLY with a raw JSON object. "
                "DO NOT include markdown formatting such as ```json. "
                "The object MUST contain exactly these keys: 'digital_inventory', 'occupancy_rate', 'media_assets', 'geographic_footprint', 'recent_ma'. "
                "Ensure it is valid JSON and parsable by Python's json.loads()."
            )
            
            config = types.GenerateContentConfig(
                system_instruction=operational_prompt[0]["content"],
                tools=[grounding_tool]
            )
            
            gemini_resp = clients["gemini"].models.generate_content(
                model=llm_config["gemini_model"],
                contents=operational_prompt[1]["content"] + json_instruction,
                config=config,
            )
            
            raw_output = gemini_resp.text.strip()
            
            # Extract JSON
            if "```json" in raw_output:
                start = raw_output.find("```json") + 7
                end = raw_output.find("```", start)
                json_text = raw_output[start:end].strip()
            elif "```" in raw_output:
                start = raw_output.find("```") + 3
                end = raw_output.find("```", start)
                json_text = raw_output[start:end].strip()
            else:
                json_text = raw_output
                
            metrics_data = json.loads(json_text)
            all_metrics["gemini"] = metrics_data
            
            # Print results summary
            _log(logger, f"\n✅ Gemini (gemini-2.5-pro) - Operational Metrics for {company_name}:")
            for key, value in metrics_data.items():
                _log(logger, f"   • {key.replace('_', ' ').title()}: {value}")
                
        except Exception as e:
            _log(logger, f"\n❌ Gemini (gemini-2.5-pro) - Operational Metrics for {company_name}: ERROR - {str(e)}")
    
    # Aggregate results using OpenAI for better synthesis
    if all_metrics and llm_enabled.get("openai") and clients.get("openai"):
        try:
            # Prepare aggregation prompt
            aggregation_prompt = [
                {
                    "role": "system",
                    "content": f"You are a financial analyst synthesizing operational data for {company_name}. "
                             "Combine information from multiple sources into single, accurate statements."
                },
                {
                    "role": "user",
                    "content": f"Here is operational data from multiple sources:\n{json.dumps(all_metrics, indent=2)}\n\n"
                             "Synthesize this into single, factual statements for each metric. "
                             "If sources conflict, use the most specific/recent data. "
                             "If no real data exists, use 'Not disclosed'. "
                             "Return JSON with keys: digital_inventory, occupancy_rate, media_assets, geographic_footprint, recent_ma"
                }
            ]
            
            # Make aggregation call with gpt-4.1 and structured output
            response = clients["openai"].responses.create(
                model=llm_config["openai_model"],
                input=aggregation_prompt,
                background=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "aggregated_metrics",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "digital_inventory": {"type": "string"},
                                "occupancy_rate": {"type": "string"},
                                "media_assets": {"type": "string"},
                                "geographic_footprint": {"type": "string"},
                                "recent_ma": {"type": "string"}
                            },
                            "required": ["digital_inventory", "occupancy_rate", "media_assets", "geographic_footprint", "recent_ma"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }, reasoning={"effort": "low"}
            )
            response_text = response.output_text
            
            # Parse aggregated response (structured output returns clean JSON)
            final_metrics = json.loads(response_text)
            _log(logger, f"\n✅ Aggregated operational metrics using OpenAI ({llm_config['openai_model']})")
            for key, value in final_metrics.items():
                _log(logger, f"   → {key.replace('_', ' ').title()}: {value}")
            return final_metrics
            
        except Exception as e:
            _log(logger, f"OpenAI aggregation error, falling back to simple merge: {e}")
    
    # Fallback: Simple aggregation - prefer non-"Not disclosed" values
    final_metrics = {
        "digital_inventory": "Not disclosed",
        "occupancy_rate": "Not disclosed",
        "media_assets": "Not disclosed",
        "geographic_footprint": "Not disclosed",
        "recent_ma": "Not disclosed"
    }
    
    for source, metrics in all_metrics.items():
        for key, value in metrics.items():
            if value and value != "Not disclosed" and final_metrics[key] == "Not disclosed":
                final_metrics[key] = value
    
    return final_metrics

def fetch_categorized_news(company_name, ticker_symbol, llm_enabled, llm_config, clients):
    """
    Fetch and categorize news for Section D using LLM web search
    Following the exact pattern as fetch_ai_news()
    """
    # Backwards compatibility wrapper: allow optional logger via kwargs
    logger = None
    if isinstance(llm_config, dict) and llm_config.get("__logger__"):
        logger = llm_config.get("__logger__")
    _log(logger, f"\n📰 Fetching categorized news for {company_name} ({ticker_symbol})...")
    
    from datetime import datetime, timedelta
    
    # Date range for news search (past week)
    today = datetime.now()
    start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    # Create prompt in the same format as news prompts
    news_prompt = [
        {
            "role": "system",
            "content": (
                f"Today's date is {end_date}. "
                f"You are a professional news analyst researching {company_name} ({ticker_symbol}), "
                "an out-of-home advertising company. You must search online using real web sources and "
                "categorize recent news into specific categories. Focus on official announcements, "
                "press releases, and reliable financial news sources. "
                "Only include news from the specified date range."
            )
        },
        {
            "role": "user",
            "content": (
                f"Today is {end_date}. Search for news about {company_name} from {start_date} to {end_date}. "
                "Categorize findings into these exact categories:\n"
                "1. earnings - Earnings releases, guidance updates, financial results\n"
                "2. strategic - Strategic announcements, tech rollouts, expansion plans\n"
                "3. leadership - CEO or executive leadership changes\n"
                "4. regulatory - Regulatory issues, legal matters, compliance\n"
                "5. sentiment - Market sentiment changes, analyst rating updates\n\n"
                "Return as JSON object with these exact keys. For each key, provide a brief "
                "summary of relevant news or 'None' if no news found in that category. "
                "Only include news that was published within the specified date range."
            )
        }
    ]
    
    all_categorized = {}
    
    # OpenAI
    if llm_enabled.get("openai") and clients.get("openai"):
        try:
            is_deep_research = "deep-research" in llm_config["openai_model"].lower()
            background = False
            
            if is_deep_research:
                modified_prompt = news_prompt.copy()
                modified_prompt[-1]["content"] += (
                    "\n\nIMPORTANT: Return your response as a valid JSON object with exactly these keys:\n"
                    "{\n"
                    '  "earnings": "summary or None",\n'
                    '  "strategic": "summary or None",\n'
                    '  "leadership": "summary or None",\n'
                    '  "regulatory": "summary or None",\n'
                    '  "sentiment": "summary or None"\n'
                    "}\n\n"
                    "Ensure the response is valid JSON that can be parsed."
                )
                
                response = clients["openai"].responses.create(
                    model=llm_config["openai_model"],
                    input=modified_prompt,
                    tools=[{"type": "web_search_preview"}],
                    background=background
                )
                response_text = response.output_text
            else:
                response = clients["openai"].responses.create(
                    model=llm_config["openai_model"],
                    input=news_prompt,
                    tools=[{"type": "web_search_preview"}],
                    background=background,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "categorized_news",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "earnings": {"type": "string"},
                                    "strategic": {"type": "string"},
                                    "leadership": {"type": "string"},
                                    "regulatory": {"type": "string"},
                                    "sentiment": {"type": "string"}
                                },
                                "required": ["earnings", "strategic", "leadership", "regulatory", "sentiment"],
                                "additionalProperties": False
                            },
                            "strict": True
                        }
                    }, 
                    reasoning={"effort": "low"}
                )
                response_text = response.output_text
            
            # Parse response
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text.strip()
            
            news_data = json.loads(json_text)
            all_categorized["openai"] = news_data
            
            # Print results summary
            _log(logger, f"\n✅ OpenAI ({llm_config['openai_model']}) - Categorized News for {company_name}:")
            categories_found = 0
            for key, value in news_data.items():
                if value and value != "None":
                    categories_found += 1
                    _log(logger, f"   • {key.title()}: {value[:100]}..." if len(value) > 100 else f"   • {key.title()}: {value}")
            if categories_found == 0:
                _log(logger, "   • No news found in any category")
                
        except Exception as e:
            _log(logger, f"\n❌ OpenAI ({llm_config['openai_model']}) - Categorized News for {company_name}: ERROR - {str(e)}")
    
    # Perplexity
    if llm_enabled.get("perplexity"):
        try:
            r = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {llm_config.get('perplexity_api_key', '')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": llm_config["perplexity_model"],
                    "messages": news_prompt,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "earnings": {"type": "string"},
                                    "strategic": {"type": "string"},
                                    "leadership": {"type": "string"},
                                    "regulatory": {"type": "string"},
                                    "sentiment": {"type": "string"}
                                },
                                "required": ["earnings", "strategic", "leadership", "regulatory", "sentiment"]
                            }
                        }
                    }
                },
                timeout=30
            )
            news_data = json.loads(r.json()["choices"][0]["message"]["content"])
            all_categorized["perplexity"] = news_data
            
            # Print results summary
            _log(logger, f"\n✅ Perplexity (sonar-pro) - Categorized News for {company_name}:")
            categories_found = 0
            for key, value in news_data.items():
                if value and value != "None":
                    categories_found += 1
                    _log(logger, f"   • {key.title()}: {value[:100]}..." if len(value) > 100 else f"   • {key.title()}: {value}")
            if categories_found == 0:
                _log(logger, "   • No news found in any category")
                
        except Exception as e:
            _log(logger, f"\n❌ Perplexity (sonar-pro) - Categorized News for {company_name}: ERROR - {str(e)}")
    
    # Gemini
    if llm_enabled.get("gemini") and clients.get("gemini"):
        try:
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            json_instruction = (
                "\n\nRespond ONLY with a raw JSON object. "
                "DO NOT include markdown formatting such as ```json. "
                "The object MUST contain exactly these keys: 'earnings', 'strategic', 'leadership', 'regulatory', 'sentiment'. "
                "Ensure it is valid JSON and parsable by Python's json.loads()."
            )
            
            config = types.GenerateContentConfig(
                system_instruction=news_prompt[0]["content"],
                tools=[grounding_tool]
            )
            
            gemini_resp = clients["gemini"].models.generate_content(
                model=llm_config["gemini_model"],
                contents=news_prompt[1]["content"] + json_instruction,
                config=config,
            )
            
            raw_output = gemini_resp.text.strip()
            
            # Extract JSON
            if "```json" in raw_output:
                start = raw_output.find("```json") + 7
                end = raw_output.find("```", start)
                json_text = raw_output[start:end].strip()
            elif "```" in raw_output:
                start = raw_output.find("```") + 3
                end = raw_output.find("```", start)
                json_text = raw_output[start:end].strip()
            else:
                json_text = raw_output
                
            news_data = json.loads(json_text)
            all_categorized["gemini"] = news_data
            
            # Print results summary
            _log(logger, f"\n✅ Gemini (gemini-2.5-pro) - Categorized News for {company_name}:")
            categories_found = 0
            for key, value in news_data.items():
                if value and value != "None":
                    categories_found += 1
                    _log(logger, f"   • {key.title()}: {value[:100]}..." if len(value) > 100 else f"   • {key.title()}: {value}")
            if categories_found == 0:
                _log(logger, "   • No news found in any category")
                
        except Exception as e:
            _log(logger, f"\n❌ Gemini (gemini-2.5-pro) - Categorized News for {company_name}: ERROR - {str(e)}")
    
    # Aggregate results using OpenAI for better synthesis
    if all_categorized and llm_enabled.get("openai") and clients.get("openai"):
        try:
            # Prepare aggregation prompt
            aggregation_prompt = [
                {
                    "role": "system",
                    "content": f"You are a news analyst synthesizing categorized news for {company_name}. "
                             "Combine information from multiple sources into single, comprehensive summaries."
                },
                {
                    "role": "user",
                    "content": f"Here is categorized news from multiple sources:\n{json.dumps(all_categorized, indent=2)}\n\n"
                             "Synthesize this into single, comprehensive summaries for each category. "
                             "Combine related information, remove duplicates, and create coherent summaries. "
                             "If no news exists for a category, use 'None'. "
                             "Return JSON with keys: earnings, strategic, leadership, regulatory, sentiment"
                }
            ]
            
            # Make aggregation call with gpt-4.1 and structured output
            response = clients["openai"].responses.create(
                model=llm_config["openai_model"],
                input=aggregation_prompt,
                background=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "aggregated_news",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "earnings": {"type": "string"},
                                "strategic": {"type": "string"},
                                "leadership": {"type": "string"},
                                "regulatory": {"type": "string"},
                                "sentiment": {"type": "string"}
                            },
                            "required": ["earnings", "strategic", "leadership", "regulatory", "sentiment"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }, 
                reasoning={"effort": "low"}
            )
            response_text = response.output_text
            
            # Parse aggregated response (structured output returns clean JSON)
            final_categorized = json.loads(response_text)
            _log(logger, f"\n✅ Aggregated categorized news using OpenAI ({llm_config['openai_model']})")
            categories_with_news = 0
            for key, value in final_categorized.items():
                if value and value != "None":
                    categories_with_news += 1
                    _log(logger, f"   → {key.title()}: {value[:100]}..." if len(value) > 100 else f"   → {key.title()}: {value}")
            _log(logger, f"   → Total categories with news: {categories_with_news}/5")
            return final_categorized
            
        except Exception as e:
            _log(logger, f"OpenAI aggregation error, falling back to simple merge: {e}")
    
    # Fallback: Simple aggregation - prefer non-"None" values
    final_categorized = {
        "earnings": "None",
        "strategic": "None",
        "leadership": "None",
        "regulatory": "None",
        "sentiment": "None"
    }
    
    for source, news in all_categorized.items():
        for key, value in news.items():
            if value and value != "None" and final_categorized[key] == "None":
                final_categorized[key] = value
    
    return final_categorized

def fetch_company_news_items(company_name, ticker_symbol, llm_enabled, llm_config, clients, logger=None, max_items=3):
    """
    Fetch latest company-specific news items using the same multi-LLM web search style
    Returns a list of dicts: {title, publisher, link}
    """
    _log(logger, f"\n📰 Searching company news for {company_name} ({ticker_symbol})...")

    today = datetime.now()
    start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    # Prompt asking for a small list of news items
    news_prompt = [
        {
            "role": "system",
            "content": (
                f"Today's date is {end_date}. "
                f"You are a professional news analyst. Find the most relevant and recent news about {company_name} ({ticker_symbol}). "
                "Focus on official announcements, earnings/strategy updates, and reputable press coverage within the date range. "
                f"Only include news from {start_date} to {end_date}."
            )
        },
        {
            "role": "user",
            "content": (
                f"Return up to {max_items} items as a JSON array of objects with keys: title, publisher, link, date. "
                "Use reputable sources and ensure links are accessible."
            )
        }
    ]

    all_items = []

    # OpenAI
    if llm_enabled.get("openai") and clients.get("openai"):
        try:
            response = clients["openai"].responses.create(
                model=llm_config["openai_model"],
                input=news_prompt,
                tools=[{"type": "web_search_preview"}],
                background=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "company_news_items",
                        "schema": {
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
                                            "date": {"type": "string"}
                                        },
                                        "required": ["title", "publisher", "link", "date"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["items"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                reasoning={"effort": "low"}
            )
            parsed_obj = json.loads(response.output_text)
            items = parsed_obj.get("items", [])
            _log(logger, f"\n✅ OpenAI ({llm_config['openai_model']}) - Company News: {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            _log(logger, f"\n❌ OpenAI ({llm_config['openai_model']}) - Company News: ERROR - {str(e)}")

    # Perplexity
    if llm_enabled.get("perplexity"):
        try:
            r = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {llm_config.get('perplexity_api_key', '')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": llm_config["perplexity_model"],
                    "messages": news_prompt,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "publisher": {"type": "string"},
                                        "link": {"type": "string"},
                                        "date": {"type": "string"}
                                    },
                                    "required": ["title", "publisher", "link", "date"]
                                }
                            }
                        }
                    }
                }, timeout=30
            )
            items = json.loads(r.json()["choices"][0]["message"]["content"])
            _log(logger, f"\n✅ Perplexity ({llm_config['perplexity_model']}) - Company News: {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            _log(logger, f"\n❌ Perplexity ({llm_config['perplexity_model']}) - Company News: ERROR - {str(e)}")

    # Gemini
    if llm_enabled.get("gemini") and clients.get("gemini"):
        try:
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            json_instruction = (
                "\n\nRespond ONLY with a raw JSON array of objects. "
                "DO NOT include markdown code fences. "
                "Each object MUST have keys: 'title', 'publisher', 'link', 'date'."
            )
            config = types.GenerateContentConfig(
                system_instruction=news_prompt[0]["content"],
                tools=[grounding_tool]
            )
            gemini_resp = clients["gemini"].models.generate_content(
                model=llm_config["gemini_model"],
                contents=news_prompt[1]["content"] + json_instruction,
                config=config,
            )
            raw_output = gemini_resp.text.strip()
            if "```json" in raw_output:
                start = raw_output.find("```json") + 7
                end = raw_output.find("```", start)
                json_text = raw_output[start:end].strip()
            elif "```" in raw_output:
                start = raw_output.find("```") + 3
                end = raw_output.find("```", start)
                json_text = raw_output[start:end].strip()
            else:
                json_text = raw_output
            items = json.loads(json_text)
            _log(logger, f"\n✅ Gemini ({llm_config['gemini_model']}) - Company News: {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            _log(logger, f"\n❌ Gemini ({llm_config['gemini_model']}) - Company News: ERROR - {str(e)}")

    # Refine & select top items using OpenAI (same strategy as email refine)
    refined_items = None
    if all_items and llm_enabled.get("openai") and clients.get("openai"):
        try:
            refine_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are an assistant cleaning and selecting company news items.\n\n"
                        "Tasks:\n"
                        f"1) De-duplicate near-identical stories.\n2) Select at most {max_items} most relevant items for {company_name} ({ticker_symbol}).\n"
                        "3) Prefer recent, credible sources; keep titles concise and correct publishers; ensure working links.\n\n"
                        "Return only the final list in the same JSON shape."
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps({"items": all_items})
                }
            ]
            resp = clients["openai"].responses.create(
                model=llm_config["openai_model"],
                input=refine_prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "refined_company_news",
                        "schema": {
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
                                            "date": {"type": "string"}
                                        },
                                        "required": ["title", "publisher", "link", "date"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["items"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                reasoning={"effort": "low"}
            )
            parsed = json.loads(resp.output_text)
            refined_items = parsed.get("items", [])[:max_items]
            _log(logger, f"\n✅ Refined company news: {len(refined_items)} selected")
        except Exception as e:
            _log(logger, f"\n⚠️ Refine company news failed: {e}")

    # Simple dedupe and trim (fallback when refine not available)
    if refined_items is None:
        seen = set()
        deduped = []
        for it in all_items:
            key = (it.get("title", "").strip().lower(), it.get("link", "").strip().lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
            if len(deduped) >= max_items:
                break
        selected = deduped
    else:
        selected = refined_items

    # Map to expected shape for HTML
    news_items = []
    for it in selected:
        news_items.append({
            "title": it.get("title", ""),
            "publisher": it.get("publisher", ""),
            "link": it.get("link", "")
        })
    return news_items

def get_comprehensive_stock_metrics(ticker_symbol, company_name, llm_enabled=None, llm_config=None, clients=None, logger=None):
    """
    Fetch comprehensive stock metrics for OOH media companies
    Returns dict with all requested metrics organized by sections
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Sequential info and historical data fetches
        info = ticker.info
        hist_1y = ticker.history(period="1y")
        hist_1w = ticker.history(period="7d")
        
        # Calculate metrics
        current_price = info.get('currentPrice', 0)
        if current_price == 0 and len(hist_1w) > 0:
            current_price = hist_1w['Close'].iloc[-1]
        
        # Week over week change
        if len(hist_1w) >= 2:
            week_ago_price = hist_1w['Close'].iloc[0]
            wow_change = ((current_price - week_ago_price) / week_ago_price * 100) if week_ago_price > 0 else 0
        else:
            wow_change = 0
        
        # 52-week high/low
        if len(hist_1y) > 0:
            week_52_high = hist_1y['High'].max()
            week_52_low = hist_1y['Low'].min()
        else:
            week_52_high = info.get('fiftyTwoWeekHigh', 0)
            week_52_low = info.get('fiftyTwoWeekLow', 0)
        
        # Trading volume (7-day average)
        if len(hist_1w) > 0:
            avg_volume_7d = hist_1w['Volume'].mean()
        else:
            avg_volume_7d = info.get('averageVolume', 0)
        
        # Format large numbers
        def format_number(num):
            if num >= 1e9:
                return f"{num/1e9:.2f}B"
            elif num >= 1e6:
                return f"{num/1e6:.2f}M"
            elif num >= 1e3:
                return f"{num/1e3:.2f}K"
            else:
                return f"{num:.2f}"
        
        # Extract numeric fields with proper None checks
        beta = info.get('beta', None)
        dividend_yield = info.get('dividendYield', None)
        trailing_pe = info.get('trailingPE', None)
        enterprise_to_ebitda = info.get('enterpriseToEbitda', None)

        # Section A: Market Performance Snapshot
        section_a = {
            "Current Price": f" ${current_price:.2f}",
            "% Change WoW": f" {wow_change:+.2f}%",
            "52-Week High/Low": f" ${week_52_high:.2f} / ${week_52_low:.2f}",
            "Market Cap": f" {format_number(info.get('marketCap', 0))}",
            "Volume (7d avg)": f" {format_number(avg_volume_7d)}",
            "Beta": f" {beta:.2f}" if beta is not None else ' N/A',
            "Dividend Yield": f" {dividend_yield * 100:.2f}%" if dividend_yield is not None else ' N/A',
            "P/E Ratio": f" {trailing_pe:.2f}" if trailing_pe is not None else ' N/A',
            "EV/EBITDA": f" {enterprise_to_ebitda:.2f}" if enterprise_to_ebitda is not None else ' N/A'
        }
        
        # Section B: Key Financials
        revenue_ttm = info.get('totalRevenue', 0)
        ebitda = info.get('ebitda', 0)
        net_income = info.get('netIncomeToCommon', 0)
        ebitda_margin = (ebitda / revenue_ttm * 100) if revenue_ttm > 0 else 0
        
        section_b = {
            "TTM Revenue": f" {format_number(revenue_ttm)}",
            "TTM EBITDA": f" {format_number(ebitda)}",
            "Net Profit": f" {format_number(net_income)}",
            "EBITDA Margin": f" {ebitda_margin:.1f}%",
            "Net Debt": f" {format_number(info.get('totalDebt', 0) - info.get('totalCash', 0))}",
            "Debt-to-Equity": f" {info.get('debtToEquity', 'N/A'):.2f}" if info.get('debtToEquity') else ' N/A',
            "Free Cash Flow": f" {format_number(info.get('freeCashflow', 0))}"
        }
        
        # Section C: Operational Indicators (fetch via LLM if enabled)
        categorized_news = None
        if llm_enabled and llm_config and clients:
            # Sequential LLM calls for operational and categorized news
            llm_config_with_logger = dict(llm_config)
            llm_config_with_logger["__logger__"] = logger
            try:
                operational_data = fetch_operational_metrics(
                    company_name, ticker_symbol, llm_enabled, llm_config_with_logger, clients
                )
            except Exception:
                operational_data = {}
            try:
                categorized_news = fetch_categorized_news(
                    company_name, ticker_symbol, llm_enabled, llm_config_with_logger, clients
                )
            except Exception:
                categorized_news = None

            section_c = {
                "% Digital Inventory": operational_data.get("digital_inventory", "Not disclosed"),
                "Occupancy Rate": operational_data.get("occupancy_rate", "Not disclosed"),
                "Media Assets": operational_data.get("media_assets", "Not disclosed"),
                "Geographic Footprint": operational_data.get("geographic_footprint", info.get('country', 'N/A')),
                "Recent M&A": operational_data.get("recent_ma", "None reported")
            }
        else:
            section_c = {
                "% Digital Inventory": "Data pending",
                "Occupancy Rate": "Data pending",
                "Media Assets": "Data pending",
                "Geographic Footprint": info.get('country', 'N/A'),
                "Recent M&A": "See news section"
            }
        
        # Section D: News & Signals (fetch concurrently)
        def _fetch_news_items():
            # Use LLM pipeline instead of yfinance.news if enabled
            try:
                if llm_enabled and llm_config and clients:
                    items = fetch_company_news_items(company_name, ticker_symbol, llm_enabled, llm_config, clients, logger=logger, max_items=3)
                else:
                    items = []
            except Exception:
                items = []
            return items

        def _fetch_analyst_signal():
            try:
                recommendations = ticker.recommendations
                if recommendations is not None and len(recommendations) > 0:
                    latest_rec = recommendations.iloc[-1]
                    return f"Latest: {latest_rec.get('toGrade', 'N/A')} by {latest_rec.get('firm', 'N/A')}"
                return "No recent updates"
            except Exception:
                return "N/A"

        # Sequential news and analyst signal
        news_items = _fetch_news_items()
        analyst_signal = _fetch_analyst_signal()
        
        # Get categorized news if not already fetched above
        if llm_enabled and llm_config and clients and categorized_news is None:
            categorized_news = fetch_categorized_news(company_name, ticker_symbol, llm_enabled, llm_config, clients)
        
        return {
            'company': company_name,
            'ticker': ticker_symbol,
            'section_a': section_a,
            'section_b': section_b,
            'section_c': section_c,
            'news': news_items,
            'analyst_signal': analyst_signal,
            'categorized_news': categorized_news,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
    except Exception as e:
        _log(logger, f"Error fetching data for {ticker_symbol}: {str(e)}")
        return {
            'company': company_name,
            'ticker': ticker_symbol,
            'error': str(e),
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M")
        }


def format_metrics_html(all_metrics, stock_charts):
    """
    Format all stock metrics into a professional HTML report with integrated charts
    """
    html = """
    <h2 style="color:#fff;margin-top:30px;">📊 Weekly OOH Media Company Tracker</h2>
    <p style="color:#aaa;font-size:14px;">Last updated: """ + datetime.now().strftime("%B %d, %Y at %I:%M %p") + """</p>
    """
    for metrics in all_metrics:
        if 'error' in metrics:
            html += f"""
            <div style="background:#222;border:1px solid #444;border-radius:8px;padding:20px;margin-bottom:20px;">
                <h3 style="color:#ff6b6b;margin-top:0;">{metrics['company']} ({metrics['ticker']}) - Error</h3>
                <p style="color:#ff6b6b;">Unable to fetch data: {metrics['error']}</p>
            </div>
            """
            continue
        
        # Determine color based on WoW change
        wow_text = metrics['section_a']['% Change WoW']
        wow_value = float(wow_text.replace('%', '').replace('+', ''))
        wow_color = '#4CAF50' if wow_value > 0 else '#ff6b6b' if wow_value < 0 else '#ffa726'
        
        # Get chart image CID
        cid = metrics['ticker'].replace('.', '').replace('-', '')
        
        html += f"""
        <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:20px;margin-bottom:20px;">
            <h3 style="color:#4fc3f7;margin-top:0;">
                {metrics['company']} ({metrics['ticker']}) 
                <span style="color:{wow_color};font-size:18px;margin-left:10px;">{wow_text}</span>
            </h3>
            
            <!-- Main Layout: All metrics and chart stacked vertically -->
            <div style="margin-top:20px;">
                
                <!-- Metrics Section -->
                <div>
                    <!-- Two columns for metrics -->
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        
                        <!-- Market Performance Column -->
                        <div>
                            <h4 style="color:#fff;margin:0 0 15px 0;font-size:14px;text-transform:uppercase;letter-spacing:1px;">
                                Market Performance
                            </h4>
                            <div style="display:flex;flex-direction:column;gap:10px;">
        """
        
        # Split section_a metrics
        section_a_items = list(metrics['section_a'].items())
        for key, value in section_a_items[:5]:  # First 5 items
            html += f"""
                                <div style="background:#222;padding:8px 12px;border-radius:4px;display:flex;justify-content:space-between;align-items:center;">
                                    <span style="color:#888;font-size:12px;margin-right:20px;">{key}</span>
                                    <span style="color:#fff;font-size:13px;font-weight:bold;">{value}</span>
                                </div>
            """
        
        html += """
                            </div>
                        </div>
                        
                        <!-- Key Financials Column -->
                        <div>
                            <h4 style="color:#fff;margin:0 0 15px 0;font-size:14px;text-transform:uppercase;letter-spacing:1px;">
                                Key Financials
                            </h4>
                            <div style="display:flex;flex-direction:column;gap:10px;">
        """
        
        # Key financials
        for key, value in list(metrics['section_b'].items())[:5]:  # First 5 items
            html += f"""
                                <div style="background:#222;padding:8px 12px;border-radius:4px;display:flex;justify-content:space-between;align-items:center;">
                                    <span style="color:#888;font-size:12px;margin-right:20px;">{key}</span>
                                    <span style="color:#fff;font-size:13px;font-weight:bold;">{value}</span>
                                </div>
            """
        
        html += f"""
                            </div>
                        </div>
                    </div>
                    
                    <!-- Third row: Additional Metrics exactly like Market Performance -->
                    <div style="margin-top:20px;">
                        <h4 style="color:#fff;margin:0 0 15px 0;font-size:14px;text-transform:uppercase;letter-spacing:1px;">
                            Additional Metrics
                        </h4>
                        <div style="display:flex;flex-direction:column;gap:10px;">
        """
        
        # Remaining metrics from section A and B
        remaining_a = section_a_items[5:]
        remaining_b = list(metrics['section_b'].items())[5:]
        
        for key, value in remaining_a + remaining_b:
            html += f"""
                                <div style="background:#222;padding:8px 12px;border-radius:4px;display:flex;justify-content:space-between;align-items:center;">
                                    <span style="color:#888;font-size:12px;margin-right:20px;">{key}</span>
                                    <span style="color:#fff;font-size:13px;font-weight:bold;">{value}</span>
                                </div>
            """
        
        html += f"""
                        </div>
                    </div>
                    
                    <!-- Chart Section after metrics -->
                    <div style="margin-top:20px;background:#0a0a0a;border-radius:8px;padding:5px 40px;">
                        <img src="cid:{cid}" style="width:100%;height:450px;object-fit:contain;border-radius:4px;">
                    </div>
                    
                    <!-- News Section after chart -->
                    <div style="margin-top:20px;padding-top:20px;border-top:1px solid #333;">
                        <h4 style="color:#fff;margin:0 0 10px 0;font-size:14px;">Latest News & Analyst Signals</h4>
                        <ul style="padding-left:20px;margin:0;list-style-type:none;">
        """
        
        # Add news items
        if metrics.get('news'):
            for i, news_item in enumerate(metrics['news'][:3]):  # Show 3 news items
                html += f"""
                        <li style="color:#ccc;margin-bottom:8px;padding-left:20px;position:relative;">
                            <span style="position:absolute;left:0;color:#4fc3f7;">▸</span>
                            <a href="{news_item['link']}" style="color:#4fc3f7;text-decoration:none;font-size:13px;">
                                {news_item['title'][:100]}{'...' if len(news_item['title']) > 100 else ''}
                            </a>
                            <span style="color:#666;font-size:11px;"> - {news_item['publisher']}</span>
                        </li>
                """
        else:
            html += """
                        <li style="color:#666;font-style:italic;">No recent news available</li>
            """
        
        html += f"""
                        </ul>
                        <p style="color:#888;font-size:12px;margin:10px 0 0 20px;">
                            <strong>Analyst Rating:</strong> {metrics.get('analyst_signal', 'N/A')}
                        </p>
        """
        
        # Add categorized news if available
        if metrics.get('categorized_news'):
            html += """
                        <div style="margin-top:15px;padding-top:15px;border-top:1px solid #333;">
                            <h5 style="color:#fff;margin:0 0 10px 20px;font-size:13px;">Categorized Updates:</h5>
                            <ul style="padding-left:40px;margin:0;list-style-type:none;font-size:12px;">
            """
            
            categories = {
                'earnings': '📊 Earnings/Guidance',
                'strategic': '🚀 Strategic Announcements', 
                'leadership': '👔 Leadership Changes',
                'regulatory': '⚖️ Regulatory/Legal',
                'sentiment': '📈 Market Sentiment'
            }
            
            for key, label in categories.items():
                if metrics['categorized_news'].get(key) and metrics['categorized_news'][key] != "None":
                    html += f"""
                            <li style="color:#ccc;margin-bottom:5px;">
                                <strong style="color:#4fc3f7;">{label}:</strong> {metrics['categorized_news'][key]}
                            </li>
                    """
                    
            html += """
                            </ul>
                        </div>
            """
        
        # Add Operational Updates below, styled like categorized updates
        html += """
                        <div style="margin-top:15px;padding-top:15px;border-top:1px solid #333;">
                            <h5 style=\"color:#fff;margin:0 0 10px 20px;font-size:13px;\">Operational Updates:</h5>
                            <ul style=\"padding-left:40px;margin:0;list-style-type:none;font-size:12px;\">
        """
        for key, value in metrics['section_c'].items():
            html += f"""
                            <li style=\"color:#ccc;margin-bottom:5px;\"><strong style=\"color:#4fc3f7;\">{key}:</strong> {value}</li>
            """
        html += """
                            </ul>
                        </div>
        """
        
        html += """
                    </div>
                </div>
            </div>
        </div>
        """
    
    return html


def generate_stock_summary_table(all_metrics):
    """
    Generate a summary table showing all stocks at a glance
    """
    html = """
    <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:20px;margin-bottom:30px;">
        <h3 style="color:#4fc3f7;margin-top:0;margin-bottom:20px;font-size:24px;">📊 Quick Summary - All Companies</h3>
        <table style="width:100%;border-collapse:collapse;background:#0a0a0a;border-radius:8px;overflow:hidden;">
            <thead>
                <tr style="background:#222;">
                    <th style="text-align:left;padding:12px 15px;color:#4fc3f7;font-weight:600;font-size:14px;">Company</th>
                    <th style="text-align:right;padding:12px 15px;color:#4fc3f7;font-weight:600;font-size:14px;">Price</th>
                    <th style="text-align:right;padding:12px 15px;color:#4fc3f7;font-weight:600;font-size:14px;">WoW %</th>
                    <th style="text-align:right;padding:12px 15px;color:#4fc3f7;font-weight:600;font-size:14px;">Market Cap</th>
                    <th style="text-align:right;padding:12px 15px;color:#4fc3f7;font-weight:600;font-size:14px;">P/E</th>
                    <th style="text-align:right;padding:12px 15px;color:#4fc3f7;font-weight:600;font-size:14px;">Div Yield</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for i, metrics in enumerate(all_metrics):
        if 'error' not in metrics:
            wow_text = metrics['section_a']['% Change WoW']
            wow_value = float(wow_text.replace('%', '').replace('+', ''))
            wow_color = '#4CAF50' if wow_value > 0 else '#ff6b6b' if wow_value < 0 else '#ffa726'
            
            # Alternate row backgrounds
            row_bg = '#111' if i % 2 == 0 else '#0a0a0a'
            
            html += f"""
            <tr style="background:{row_bg};">
                <td style="padding:12px 15px;color:#fff;font-weight:500;">{metrics['company']}</td>
                <td style="padding:12px 15px;text-align:right;color:#fff;font-family:monospace;">{metrics['section_a']['Current Price']}</td>
                <td style="padding:12px 15px;text-align:right;color:{wow_color};font-weight:bold;font-family:monospace;">{wow_text}</td>
                <td style="padding:12px 15px;text-align:right;color:#fff;font-family:monospace;">{metrics['section_a']['Market Cap']}</td>
                <td style="padding:12px 15px;text-align:right;color:#fff;font-family:monospace;">{metrics['section_a']['P/E Ratio']}</td>
                <td style="padding:12px 15px;text-align:right;color:#fff;font-family:monospace;">{metrics['section_a']['Dividend Yield']}</td>
            </tr>
            """
    
    html += """
            </tbody>
        </table>
    </div>
    """
    
    return html