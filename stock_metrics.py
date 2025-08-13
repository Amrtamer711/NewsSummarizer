import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import json
import requests
from google.genai import types
import concurrent.futures

# Import helper modules
from llm_core import call_openai, call_perplexity, call_gemini
from json_helpers import extract_json_from_text, format_json_schema
from stock_analysis import (
    get_operational_metrics,
    get_categorized_news,
    get_company_news_items,
    log_message as _log,
    format_large_number as format_number,
    fetch_basic_stock_data,
    calculate_market_metrics,
    calculate_financial_metrics,
    get_analyst_signal
)

def fetch_operational_metrics(company_name, ticker_symbol, llm_enabled, llm_config, clients):
    """
    Fetch operational indicators for OOH companies using LLM web search
    Following the exact pattern as fetch_ai_news()
    """
    # Backwards compatibility wrapper: allow optional logger via kwargs
    logger = None
    if isinstance(llm_config, dict) and llm_config.get("__logger__"):
        logger = llm_config.get("__logger__")
    
    # Delegate to clean helper module
    return get_operational_metrics(
        company_name=company_name,
        ticker_symbol=ticker_symbol,
        llm_enabled=llm_enabled,
        llm_config=llm_config,
        clients=clients,
        logger=logger
    )

def fetch_categorized_news(company_name, ticker_symbol, llm_enabled, llm_config, clients):
    """
    Fetch and categorize news for Section D using LLM web search
    Following the exact pattern as fetch_ai_news()
    """
    # Backwards compatibility wrapper: allow optional logger via kwargs
    logger = None
    if isinstance(llm_config, dict) and llm_config.get("__logger__"):
        logger = llm_config.get("__logger__")
    
    # Delegate to clean helper module
    return get_categorized_news(
        company_name=company_name,
        ticker_symbol=ticker_symbol,
        llm_enabled=llm_enabled,
        llm_config=llm_config,
        clients=clients,
        logger=logger
    )

def fetch_company_news_items(company_name, ticker_symbol, llm_enabled, llm_config, clients, logger=None, max_items=3):
    """
    Fetch latest company-specific news items using the same multi-LLM web search style
    Returns a list of dicts: {title, publisher, link}
    """
    # Delegate to clean helper module
    return get_company_news_items(
        company_name=company_name,
        ticker_symbol=ticker_symbol,
        llm_enabled=llm_enabled,
        llm_config=llm_config,
        clients=clients,
        logger=logger,
        max_items=max_items
    )

def get_comprehensive_stock_metrics(ticker_symbol, company_name, llm_enabled=None, llm_config=None, clients=None, logger=None):
    """
    Fetch comprehensive stock metrics for OOH media companies
    Returns dict with all requested metrics organized by sections
    """
    try:
        # Fetch basic stock data
        stock_data = fetch_basic_stock_data(ticker_symbol)
        
        # Calculate market metrics (Section A)
        section_a = calculate_market_metrics(stock_data)
        
        # Calculate financial metrics (Section B)
        section_b = calculate_financial_metrics(stock_data)
        
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
                "Geographic Footprint": operational_data.get("geographic_footprint", stock_data['info'].get('country', 'N/A')),
                "Recent M&A": operational_data.get("recent_ma", "None reported")
            }
        else:
            section_c = {
                "% Digital Inventory": "Data pending",
                "Occupancy Rate": "Data pending",
                "Media Assets": "Data pending",
                "Geographic Footprint": stock_data['info'].get('country', 'N/A'),
                "Recent M&A": "See news section"
            }
        
        # Section D: News & Signals
        # Fetch news items
        news_items = []
        if llm_enabled and llm_config and clients:
            try:
                news_items = fetch_company_news_items(
                    company_name, ticker_symbol, llm_enabled, llm_config, clients, 
                    logger=logger, max_items=3
                )
            except Exception:
                pass
        
        # Get analyst signal
        analyst_signal = get_analyst_signal(stock_data['ticker'])
        
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
                            <h5 style="color:#fff;margin:0 0 10px 20px;font-size:13px;">Operational Updates:</h5>
                            <ul style="padding-left:40px;margin:0;list-style-type:none;font-size:12px;">
        """
        for key, value in metrics['section_c'].items():
            html += f"""
                            <li style="color:#ccc;margin-bottom:5px;"><strong style="color:#4fc3f7;">{key}:</strong> {value}</li>
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