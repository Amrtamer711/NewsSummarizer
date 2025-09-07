# NewsAI - Intelligent News Aggregation System

A sophisticated news aggregation system that fetches, verifies, and curates industry-specific news using multiple AI models and traditional news APIs. The system includes advanced hallucination detection, article deduplication, and automated email digests.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Workflow Details](#workflow-details)
- [API Endpoints](#api-endpoints)
- [File Structure](#file-structure)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)

## Overview

NewsAI is an enterprise-grade news aggregation system designed to provide executives with curated, verified daily news digests across multiple industry sectors. It combines traditional news APIs with cutting-edge LLMs to ensure comprehensive coverage while eliminating hallucinated content.

### Key Capabilities

- **Multi-source aggregation**: Fetches news from OpenAI, Perplexity, Google Gemini, NewsAPI, and NewsDataAPI
- **Hallucination detection**: Verifies AI-generated articles against real search results
- **Smart deduplication**: Uses AI to identify and merge duplicate stories
- **Date verification**: Ensures articles are actually from the claimed publication date
- **URL correction**: Automatically fixes broken or redirect URLs using web search
- **Automated digests**: Sends formatted email newsletters with curated content
- **Stock analysis**: Includes market performance tracking for relevant companies

## Features

### 1. Multi-LLM News Generation
- **OpenAI (GPT-5)**: Primary content generation with structured output
- **Perplexity (Sonar Pro)**: Real-time web search integration
- **Google Gemini (2.5 Pro)**: Alternative perspective with 10 articles per section

### 2. Traditional News APIs
- **NewsAPI**: Comprehensive global news coverage
- **NewsDataAPI**: Additional news sources and regional content

### 3. Industry Sections
- UAE OOH (Out-of-Home Advertising)
- UAE Marketing
- UAE Business
- Global OOH
- Global Marketing
- Global Business

### 4. Advanced Verification System
- **Hallucination Check**: Verifies each AI article exists via web search
- **Date Validation**: Confirms publication dates with 3-day tolerance
- **URL Verification**: Replaces LLM-generated URLs with actual article links
- **Source Attribution**: Tracks which system provided each article

### 5. Content Curation
- **Deduplication**: AI-powered identification of duplicate stories
- **Quality Selection**: Chooses most credible sources
- **Article Limit**: Maximum 6 articles per section for digestibility

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   News Sources  │     │  Verification   │     │   Curation      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ • OpenAI API    │     │ • Web Search    │     │ • Deduplication │
│ • Perplexity    │────▶│ • Date Check    │────▶│ • Quality Sort  │
│ • Gemini        │     │ • URL Fix       │     │ • Limit to 6    │
│ • NewsAPI       │     │ • Title Match   │     │ • Format Output │
│ • NewsDataAPI   │     └─────────────────┘     └─────────────────┘
└─────────────────┘                                      │
                                                        ▼
                                              ┌─────────────────┐
                                              │   Distribution  │
                                              ├─────────────────┤
                                              │ • Email Digest  │
                                              │ • Web Interface │
                                              │ • Database Save │
                                              └─────────────────┘
```

## Installation

### Prerequisites

- Python 3.8+
- SQLite3
- API Keys for:
  - OpenAI
  - Perplexity
  - Google Gemini
  - NewsAPI
  - NewsDataAPI
  - SerpAPI (for verification)
  - (Optional) Outlook/Email credentials

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/NewsAI.git
   cd NewsAI
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file with your API keys:
   ```env
   # AI Model APIs
   OPENAI_API_KEY=sk-...
   PERPLEXITY_API_KEY=pplx-...
   GEMINI_API_KEY=...
   
   # News APIs
   NEWSAPI_KEY=...
   NEWSDATA_API_KEY=...
   
   # Search API (for verification)
   SERPAPI_KEY=...
   
   # Email Configuration (optional)
   OUTLOOK_EMAIL=your-email@company.com
   OUTLOOK_PASSWORD=your-app-password
   
   # Optional: Stock tracking
   POLYGON_API_KEY=...
   ALPHA_VANTAGE_API_KEY=...
   ```

5. **Initialize database**
   ```bash
   python -c "from storage import init_db; init_db()"
   ```

## Configuration

### Core Settings (`config.py`)

```python
# Database location
DATABASE_PATH = "newsai.db"

# Public URL for web interface
BASE_PUBLIC_URL = "https://your-domain.com"

# API timeouts
API_TIMEOUT = 30  # seconds
```

### LLM Configuration (`send_email.py`)

```python
# Enable/disable specific LLMs
LLM_ENABLED = {
    "openai": True,      # GPT-5
    "perplexity": True,  # Sonar Pro
    "gemini": True       # Gemini 2.5 Pro
}

# Model versions
MODEL_CONFIG = {
    "openai_model": "gpt-5",
    "perplexity_model": "sonar-pro",
    "gemini_model": "gemini-2.5-pro"
}

# Articles per section
MAX_ARTICLES_PER_SECTION = 6
```

### Date Range (`prompts.py`)

```python
# Default: fetch articles from last 3 days
today = datetime.now()
start_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
end_date = today.strftime("%Y-%m-%d")
```

## Usage

### Running the Web Interface

```bash
python app.py
```

Access at `http://localhost:3000`

### Manual News Fetch

```bash
# Fetch and save today's news
python run_today.py

# Fetch for specific date
python fetch_news.py --date 2024-01-15
```

### Scheduled Execution

Add to crontab for daily execution:
```bash
0 8 * * * cd /path/to/NewsAI && /path/to/venv/bin/python run_today.py
```

## Workflow Details

### 1. Article Fetching Phase

#### AI-Powered Fetching (`fetch_ai_news()`)

For each industry section:

**OpenAI Process:**
```python
1. Send structured prompt requesting 5 articles
2. Use JSON schema for consistent output
3. Handle deep-research mode for complex queries
4. Tag articles with "client": "OpenAI"
```

**Perplexity Process:**
```python
1. Send similar prompt with web search enabled
2. Extract JSON from markdown response
3. Parse and validate article structure
4. Tag articles with "client": "Perplexity"
```

**Gemini Process:**
```python
1. Request 10 articles (double the standard)
2. Add explicit JSON formatting instructions
3. Fix Google redirect URLs via search
4. Tag articles with "client": "Gemini"
```

#### Traditional API Fetching (`fetch_news()`)

Parallel execution using ThreadPoolExecutor:
```python
1. NewsAPI: Search with section keywords, 3-day range
2. NewsDataAPI: Similar search parameters
3. Both return up to 20 articles per section
4. Tag with respective client names
```

### 2. Verification Phase

#### Hallucination Detection (`check_articles_for_hallucinations()`)

Only applies to AI-sourced articles:

```python
For each article:
    1. Build search query: '"article title" source'
    2. Search Google News (primary) and Google (fallback)
    3. Use flexible date range (7 days or double requested)
    
    Title Matching:
    - Exact substring match
    - Reverse substring match
    - Word overlap threshold (>50% common words)
    
    Date Verification:
    - Parse claimed vs actual dates
    - Allow 3-day tolerance
    - Handle relative dates ("2 days ago")
    
    URL Correction:
    - Replace with verified URL from search
    - Preserve original for reference
```

### 3. Refinement Phase

#### Article Selection (`refine_articles()`)

Using OpenAI for intelligent curation:

```python
1. Send all verified articles to OpenAI
2. Instructions:
   - Identify near-duplicates
   - Select most credible source per story
   - Return maximum 6 articles
   
3. URL Preservation:
   - Store URL mappings before processing
   - Restore verified URLs after OpenAI response
   - Maintain SERP-validated links
```

### 4. Output Generation

Final digest includes:
- Up to 6 verified articles per section
- Accurate publication dates
- Working, verified URLs
- Source attribution
- Quality ranking

## API Endpoints

### Web Interface Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/saved` | GET | View saved articles |
| `/render-digest` | GET | View specific digest |
| `/fetch-and-email` | POST | Manually trigger digest |
| `/save-article` | POST | Save individual article |
| `/delete-article` | DELETE | Remove saved article |

### API Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trigger-stocks-monday` | POST | Trigger weekly stock analysis |
| `/digests` | GET | List available digests |

## File Structure

```
NewsAI/
├── app.py                 # Flask web application
├── news_fetchers.py       # Core fetching & verification logic
├── send_email.py          # Email generation & LLM orchestration
├── prompts.py             # LLM prompt templates
├── storage.py             # Database operations
├── clients.py             # API client initialization
├── config.py              # Configuration settings
├── llm_core.py            # LLM interaction utilities
├── json_helpers.py        # JSON parsing utilities
├── html_builders.py       # HTML template generation
├── notifier.py            # Email sending functionality
├── stock_analysis.py      # Stock market integration
├── requirements.txt       # Python dependencies
├── render.yaml            # Render.com deployment config
└── static/                # Static assets (charts, etc.)
```

### Key Modules

- **`news_fetchers.py`**: Core logic for fetching, verifying, and refining articles
- **`send_email.py`**: Orchestrates LLM calls and manages the overall workflow
- **`app.py`**: Web interface and API endpoints
- **`storage.py`**: SQLite database operations for persistence

## Development

### Running Tests

```bash
# Set test mode to avoid sending emails
export TEST_MODE=true
python -m pytest tests/
```

### Adding New Sections

1. Add prompt template to `prompts.py`
2. Update `SECTION_ORDER` in `send_email.py`
3. Add section logic to `fetch_ai_news()` and `fetch_news()`

### Debugging

Enable detailed logging:
```python
# In news_fetchers.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Deployment

### Render.com Deployment

1. Connect GitHub repository
2. Use provided `render.yaml` configuration
3. Set environment variables in Render dashboard
4. Deploy with automatic builds

### Docker Deployment

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### Production Considerations

- Use Redis for caching frequently accessed articles
- Implement rate limiting for API endpoints
- Add monitoring for API quota usage
- Set up error alerting for failed fetches
- Use CDN for static assets

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Style

- Follow PEP 8 guidelines
- Add type hints for function parameters
- Document complex logic with inline comments
- Write descriptive commit messages

## License

This project is proprietary software. All rights reserved.

## Support

For issues, questions, or contributions, please contact the development team or open an issue on GitHub.