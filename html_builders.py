"""
HTML building utilities for email generation.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import quote


def create_email_header(title: str, subtitle: str, date_str: str) -> str:
    """Create the main email header section."""
    return f"""
    <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:30px;margin-bottom:30px;text-align:center;">
        <h1 style="color:#4fc3f7;margin:0;font-size:36px;font-weight:600;">{title}</h1>
        <p style="color:#aaa;font-size:18px;margin:10px 0 0 0;">{date_str}</p>
        <p style="color:#ccc;font-size:16px;margin:10px 0 0 0;">{subtitle}</p>
    </div>
    """


def create_metric_box(label: str, value: str) -> str:
    """Create a single metric display box."""
    return f"""
    <div style="background:#222;padding:8px 12px;border-radius:4px;display:flex;justify-content:space-between;align-items:center;">
        <span style="color:#888;font-size:12px;margin-right:20px;">{label}</span>
        <span style="color:#fff;font-size:13px;font-weight:bold;">{value}</span>
    </div>
    """


def create_metrics_column(title: str, metrics: Dict[str, str]) -> str:
    """Create a column of metrics with title."""
    html = f"""
    <div>
        <h4 style="color:#fff;margin:0 0 15px 0;font-size:14px;text-transform:uppercase;letter-spacing:1px;">
            {title}
        </h4>
        <div style="display:flex;flex-direction:column;gap:10px;">
    """
    
    for label, value in metrics.items():
        html += create_metric_box(label, value)
    
    html += """
        </div>
    </div>
    """
    return html


def create_stock_header(company: str, ticker: str, wow_change: str, wow_color: str) -> str:
    """Create stock section header with WoW change."""
    return f"""
    <h3 style="color:#4fc3f7;margin-top:0;">
        {company} ({ticker}) 
        <span style="color:{wow_color};font-size:18px;margin-left:10px;">{wow_change}</span>
    </h3>
    """


def create_news_list(news_items: List[Dict[str, str]], max_items: int = 3) -> str:
    """Create a list of news items."""
    html = '<ul style="padding-left:20px;margin:0;list-style-type:none;">'
    
    if not news_items:
        html += '<li style="color:#666;font-style:italic;">No recent news available</li>'
    else:
        for news in news_items[:max_items]:
            html += f"""
            <li style="color:#ccc;margin-bottom:8px;padding-left:20px;position:relative;">
                <span style="position:absolute;left:0;color:#4fc3f7;">▸</span>
                <a href="{news['link']}" style="color:#4fc3f7;text-decoration:none;font-size:13px;">
                    {news['title'][:100]}{'...' if len(news['title']) > 100 else ''}
                </a>
                <span style="color:#666;font-size:11px;"> - {news['publisher']}</span>
            </li>
            """
    
    html += '</ul>'
    return html


def create_categorized_news(categorized_news: Dict[str, str]) -> str:
    """Create categorized news section."""
    if not categorized_news:
        return ""
    
    categories = {
        'earnings': '📊 Earnings/Guidance',
        'strategic': '🚀 Strategic Announcements', 
        'leadership': '👔 Leadership Changes',
        'regulatory': '⚖️ Regulatory/Legal',
        'sentiment': '📈 Market Sentiment'
    }
    
    html = """
    <div style="margin-top:15px;padding-top:15px;border-top:1px solid #333;">
        <h5 style="color:#fff;margin:0 0 10px 20px;font-size:13px;">Categorized Updates:</h5>
        <ul style="padding-left:40px;margin:0;list-style-type:none;font-size:12px;">
    """
    
    for key, label in categories.items():
        if categorized_news.get(key) and categorized_news[key] != "None":
            html += f"""
            <li style="color:#ccc;margin-bottom:5px;">
                <strong style="color:#4fc3f7;">{label}:</strong> {categorized_news[key]}
            </li>
            """
    
    html += "</ul></div>"
    return html


def create_operational_updates(metrics: Dict[str, str]) -> str:
    """Create operational updates section."""
    html = """
    <div style="margin-top:15px;padding-top:15px;border-top:1px solid #333;">
        <h5 style="color:#fff;margin:0 0 10px 20px;font-size:13px;">Operational Updates:</h5>
        <ul style="padding-left:40px;margin:0;list-style-type:none;font-size:12px;">
    """
    
    for key, value in metrics.items():
        html += f"""
        <li style="color:#ccc;margin-bottom:5px;">
            <strong style="color:#4fc3f7;">{key}:</strong> {value}
        </li>
        """
    
    html += "</ul></div>"
    return html


def create_stock_summary_row(metrics: Dict[str, Any], index: int) -> str:
    """Create a single row for stock summary table."""
    if 'error' in metrics:
        return ""
    
    wow_text = metrics['section_a']['% Change WoW']
    wow_value = float(wow_text.replace('%', '').replace('+', ''))
    wow_color = '#4CAF50' if wow_value > 0 else '#ff6b6b' if wow_value < 0 else '#ffa726'
    row_bg = '#111' if index % 2 == 0 else '#0a0a0a'
    
    return f"""
    <tr style="background:{row_bg};">
        <td style="padding:12px 15px;color:#fff;font-weight:500;">{metrics['company']}</td>
        <td style="padding:12px 15px;text-align:right;color:#fff;font-family:monospace;">{metrics['section_a']['Current Price']}</td>
        <td style="padding:12px 15px;text-align:right;color:{wow_color};font-weight:bold;font-family:monospace;">{wow_text}</td>
        <td style="padding:12px 15px;text-align:right;color:#fff;font-family:monospace;">{metrics['section_a']['Market Cap']}</td>
        <td style="padding:12px 15px;text-align:right;color:#fff;font-family:monospace;">{metrics['section_a']['P/E Ratio']}</td>
        <td style="padding:12px 15px;text-align:right;color:#fff;font-family:monospace;">{metrics['section_a']['Dividend Yield']}</td>
    </tr>
    """


def create_news_article_item(
    article: Dict[str, str],
    section: str,
    save_button_enabled: bool = False,
    script_url: str = ""
) -> str:
    """Create a single news article item with optional save button."""
    title = article.get("title", "Untitled")
    url = article.get("url", "#")
    desc = article.get("summary", "")
    
    save_button = ""
    if save_button_enabled and script_url:
        save_url = f"{script_url}?"
        save_url += f"title={quote(title)}"
        save_url += f"&url={quote(url)}"
        save_url += f"&section={quote(section)}"
        save_url += f"&summary={quote(desc[:500])}"
        
        save_button = f'''
        <a href="{save_url}" target="_blank" 
           style="float:right;background:#4CAF50;color:white;padding:4px 8px;
                  border-radius:4px;text-decoration:none;font-size:12px;margin-left:10px;">
            Save 📌
        </a>
        '''
    
    desc_html = f"<p style='margin:4px 0 10px 0;color:#ccc;font-size:14px;'>{desc}</p>" if desc else ""
    
    return f"""
    <li style='margin-bottom:15px;border-bottom:1px solid #333;padding-bottom:15px;'>
        {save_button}
        <a href='{url}' style='color:#4fc3f7;font-weight:bold;text-decoration:none;font-size:16px;display:block;margin-bottom:5px;'>
            {title}
        </a>
        {desc_html}
    </li>
    """


def create_chart_placeholder(ticker: str) -> str:
    """Create image placeholder for stock chart."""
    cid = ticker.replace('.', '').replace('-', '')
    return f"""
    <div style="margin-top:20px;background:#0a0a0a;border-radius:8px;padding:5px 40px;">
        <img src="cid:{cid}" style="width:100%;height:450px;object-fit:contain;border-radius:4px;">
    </div>
    """


def wrap_in_container(content: str) -> str:
    """Wrap content in the main email container."""
    return f"""
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
            {content}
            <p style="margin-top:20px;color:#aaa;font-size:13px;text-align:center;">✅ Auto-generated by your digest bot</p>
        </div>
    </body>
    </html>
    """