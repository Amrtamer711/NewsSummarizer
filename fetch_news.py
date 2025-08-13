import os
from dotenv import load_dotenv
from newsapi import NewsApiClient
from newsdataapi import NewsDataApiClient  # Official class name from PyPI:contentReference[oaicite:2]{index=2}
from config import NEWS_API_KEY, NEWS_IO_KEY

# Initialize API clients
newsapi_client = NewsApiClient(api_key=NEWS_API_KEY)
newsdata_client = NewsDataApiClient(apikey=NEWS_IO_KEY)

def fetch_newsapi():
    response = newsapi_client.get_everything(
        q="(OOH OR Out Of Home OR UAE Billboard Industry OR marketing OR advertising OR 'business UAE')",
        language="en",
        sort_by="publishedAt",
        page_size=5,
    )
    return [f"📰 {a['title']}\n{a['url']}" for a in response.get("articles", [])]

def fetch_newsdata():
    response = newsdata_client.latest_api(
    q="OOH marketing UAE OR business",
    country="ae,us",
    language="en",
    page=0
    )
    return [f"🟦 {item['title']}\n{item['link']}" for item in response.get("results", [])[:5]]

def test_fetch_all():
    news = fetch_newsapi() + fetch_newsdata()
    print("\n--- Combined News ---\n")
    for item in news[:8]:
        print(item, "\n")
    return news

if __name__ == "__main__":
    test_fetch_all()