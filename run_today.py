#!/usr/bin/env python3
"""Run today's news collection locally"""

from datetime import datetime
from app import build_digest_for_date

if __name__ == "__main__":
    print("🚀 Running today's news collection locally...")
    
    today = datetime.now()
    result = build_digest_for_date(today)
    
    print(f"\n✅ Done! Collected:")
    for section, articles in result['sections'].items():
        print(f"  - {section}: {len(articles)} articles")
    
    if result.get('stocks_html'):
        print(f"  - Stocks data: Yes (Monday)")
    
    print(f"\n📱 View at: http://localhost:3000/")