# NewsAI - Intelligent News Aggregation & Analysis Platform

A sophisticated AI-powered news aggregation system that fetches, verifies, and curates industry-specific news from multiple sources. Features advanced hallucination detection, intelligent article deduplication, comprehensive stock market analysis, and automated email digests.

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/NewsAI.git
cd NewsAI

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Run locally
python app.py
# Visit http://localhost:3000
```

## 📋 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## ✨ Features

### Core Capabilities

- **🤖 Multi-LLM Integration**: Leverages OpenAI GPT-5, Perplexity Sonar Pro, and Google Gemini 2.5 Pro
- **🔍 Hallucination Detection**: Verifies AI-generated articles against real search results
- **📊 Stock Analysis**: Weekly comprehensive analysis of 9 major OOH advertising companies
- **📧 Automated Digests**: Daily news summaries and weekly stock reports via email
- **🗄️ Persistent Storage**: SQLite database with organized data directory structure
- **🌐 Web Interface**: Modern dark-themed UI for viewing digests and saved articles
- **⚡ Smart Deduplication**: AI-powered identification and merging of duplicate stories

### Industry Coverage

1. **UAE Markets**
   - OOH (Out-of-Home) Advertising
   - Marketing Agencies
   - General Business

2. **Global Markets**
   - OOH Advertising
   - Marketing Industry
   - Business News

### Stock Coverage (Weekly)

- Clear Channel Outdoor (CCO)
- JCDecaux (DEC.PA)
- Lamar Advertising (LAMR)
- Ocean Outdoor (ONE)
- OUTFRONT Media (OUT)
- Ströer SE (SAX.DE)
- APG SGA (APGN.SW)
- oOh!media Limited (OML.AX)
- Focus Media (002027.SZ)

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        NewsAI Platform                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   OpenAI    │  │ Perplexity  │  │   Gemini    │           │
│  │   (GPT-5)   │  │ (Sonar Pro) │  │ (2.5 Pro)   │           │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │
│         │                 │                 │                   │
│         └─────────────────┴─────────────────┘                  │
│                           │                                     │
│                    ┌──────▼──────┐                            │
│                    │ Hallucination│                            │
│                    │   Detector   │◄────── SerpAPI            │
│                    └──────┬──────┘                            │
│                           │                                     │
│  ┌──────────┐     ┌──────▼──────┐     ┌──────────┐          │
│  │ NewsAPI  ├─────►  Article     ├─────►│ OpenAI   │          │
│  └──────────┘     │ Aggregator  │     │ Refiner  │          │
│  ┌──────────┐     └──────┬──────┘     └────┬─────┘          │
│  │NewsData  │            │                  │                 │
│  └──────────┘            │                  │                 │
│                          ▼                  ▼                 │
│                    ┌─────────────────────────────┐            │
│                    │   SQLite Database (/data)   │            │
│                    └──────────┬──────────────────┘            │
│                               │                                │
│         ┌─────────────────────┼─────────────────────┐         │
│         ▼                     ▼                     ▼         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Web Interface│  │Email Digest  │  │ Stock Charts │       │
│  │  (Flask)     │  │   (SMTP)     │  │ (Matplotlib) │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/NewsAI.git
cd NewsAI
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

Create `.env` file in the root directory:

```env
# AI Model APIs (Required)
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_API_KEY=...  # For Gemini

# News APIs (Required)
NEWS_API_KEY=...
NEWS_IO_KEY=...

# Search API (Required for hallucination detection)
SERPAPI_KEY=...

# Email Configuration (Required for email digests)
OUTLOOK_SMTP_HOST=smtp.office365.com
OUTLOOK_SMTP_PORT=587
OUTLOOK_SMTP_USER=your-email@company.com
OUTLOOK_SMTP_PASS=your-app-password
OUTLOOK_NOTIFY_TO=recipient@company.com

# Stock APIs (Optional but recommended)
POLYGON_API_KEY=...
ALPHA_VANTAGE_API_KEY=...

# Application Settings (Optional)
BASE_PUBLIC_URL=http://localhost:3000
DATA_DIR=./data  # /data on production
TEST_MODE=false
```

### Step 5: Initialize Database

```bash
python -c "from storage import init_db; init_db()"
```

## ⚙️ Configuration

### LLM Selection

Edit `send_email.py` to enable/disable specific LLMs:

```python
LLM_ENABLED = {
    "openai": True,      # OpenAI GPT-5
    "perplexity": True,  # Perplexity Sonar Pro
    "gemini": True       # Google Gemini 2.5 Pro
}
```

### Model Configuration

```python
MODEL_CONFIG = {
    "openai_model": "gpt-5",
    "perplexity_model": "sonar-pro",
    "gemini_model": "gemini-2.5-pro"
}
```

### Date Range

Modify `prompts.py` to adjust the article date range:

```python
# Default: Last 3 days
start_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
end_date = today.strftime("%Y-%m-%d")
```

### Stock List

Edit `STOCKS` array in `send_email.py` to modify tracked companies.

## 🖥️ Usage

### Web Interface

```bash
python app.py
```

Navigate to `http://localhost:3000` to access:
- **Today's Digest**: Latest news compilation
- **Calendar View**: Historical digests
- **Saved Articles**: Bookmarked articles
- **Weekly Stocks**: Stock analysis (Mondays)

### Manual News Fetch

```bash
# Fetch today's news
python run_today.py

# Test mode (doesn't send emails)
TEST_MODE=true python send_email.py
```

### Production Commands

```bash
# Daily news collection (via API)
curl -X POST http://localhost:3000/api/trigger/daily-news \
  -H "X-Auth-Token: your-cron-token"

# Weekly stocks (Mondays)
curl -X POST http://localhost:3000/api/trigger/weekly-stocks \
  -H "X-Auth-Token: your-cron-token"

# Clean old charts
curl -X POST http://localhost:3000/api/cleanup-charts?days=30 \
  -H "X-Auth-Token: your-cron-token"
```

## 📚 API Documentation

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Today's digest view |
| `/render-digest?date=YYYY-MM-DD` | GET | Specific date digest |
| `/calendar` | GET | Calendar view of all digests |
| `/saved` | GET | View saved articles |
| `/stocks` | GET | Latest stock analysis |
| `/digests` | GET | JSON list of available digests |

### Protected Endpoints (Requires X-Auth-Token)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trigger/daily-news` | POST | Trigger daily news collection |
| `/api/trigger/weekly-stocks` | POST | Trigger weekly stocks + news |
| `/api/cleanup-charts` | POST | Clean old stock charts |
| `/save-article` | POST | Save an article |
| `/delete-article` | DELETE | Remove saved article |

### Save Article Format

```json
{
  "title": "Article Title",
  "url": "https://...",
  "section": "UAE OOH",
  "summary": "Article summary..."
}
```

## 🚀 Deployment

### Render.com Deployment

1. **Fork/Clone Repository**
   ```bash
   git clone https://github.com/yourusername/NewsAI.git
   ```

2. **Connect to Render**
   - Create account at https://render.com
   - Connect GitHub repository
   - Use `render.yaml` for automatic configuration

3. **Configure Environment Variables**
   
   Add all variables from `.env` file in Render dashboard:
   - All API keys
   - Email configuration
   - Set `DATA_DIR=/data`
   - Set `TEST_MODE=false`

4. **Deploy**
   - Render will automatically:
     - Deploy all services to Singapore region
     - Create web service with persistent disk (1GB)
     - Set up daily news cron job (6 AM UTC)
     - Set up weekly stocks cron job (Mondays 6 AM UTC)

### Manual Deployment

1. **Install on Server**
   ```bash
   git clone https://github.com/yourusername/NewsAI.git
   cd NewsAI
   pip install -r requirements.txt
   ```

2. **Configure SystemD Service**
   ```ini
   [Unit]
   Description=NewsAI Web Service
   After=network.target

   [Service]
   Type=simple
   User=newsai
   WorkingDirectory=/opt/newsai
   Environment="PATH=/opt/newsai/venv/bin"
   ExecStart=/opt/newsai/venv/bin/python app.py
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```

3. **Configure Cron Jobs**
   ```cron
   # Daily news at 6 AM
   0 6 * * * curl -X POST http://localhost:3000/api/trigger/daily-news -H "X-Auth-Token: $CRON_TOKEN"
   
   # Weekly stocks on Mondays
   0 6 * * 1 curl -X POST http://localhost:3000/api/trigger/weekly-stocks -H "X-Auth-Token: $CRON_TOKEN"
   ```

## 🛠️ Development

### Project Structure

```
NewsAI/
├── app.py                 # Flask web application
├── news_fetchers.py       # Core news fetching & verification
├── send_email.py          # Email generation & orchestration
├── stock_analysis.py      # Stock market data fetching
├── stock_metrics.py       # Stock metrics calculation
├── storage.py             # Database operations
├── clients.py             # API client initialization
├── config.py              # Configuration management
├── prompts.py             # LLM prompt templates
├── llm_core.py           # LLM interaction utilities
├── json_helpers.py       # JSON parsing utilities
├── html_builders.py      # HTML template generation
├── notifier.py           # Email sending functionality
├── requirements.txt      # Python dependencies
├── render.yaml           # Render.com deployment config
├── run_today.py          # Local testing script
├── .env.example          # Environment variable template
└── data/                 # Data directory (gitignored)
    ├── newsai.db         # SQLite database
    └── static/           # Generated charts
```

### Adding New Features

#### Add New Industry Section

1. Add prompt to `prompts.py`:
   ```python
   new_section_prompt = [
       {"role": "system", "content": "..."},
       {"role": "user", "content": "..."}
   ]
   ```

2. Update `SECTION_ORDER` in `send_email.py`

3. Add to prompt mapping in `fetch_ai_news()`

#### Add New Stock

1. Add to `STOCKS` array in `send_email.py`:
   ```python
   {"name": "Company Name", "ticker": "SYMBOL"}
   ```

#### Add New LLM

1. Initialize client in `clients.py`
2. Add to `LLM_ENABLED` in `send_email.py`
3. Implement fetching logic in `news_fetchers.py`

### Testing

```bash
# Run in test mode (no emails sent)
TEST_MODE=true python send_email.py

# Test specific component
python -m pytest tests/test_hallucination.py

# Test with debug logging
python -c "import logging; logging.basicConfig(level=logging.DEBUG); from app import app; app.run()"
```

## 🔧 Troubleshooting

### Common Issues

1. **"No module named 'X'"**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database locked error**
   - Ensure only one instance is running
   - Check file permissions on `/data` directory

3. **Email not sending**
   - Verify SMTP credentials
   - Check firewall rules for port 587
   - Enable "less secure apps" or use app password

4. **API rate limits**
   - Implement caching for development
   - Rotate API keys if needed
   - Add delays between requests

5. **No stock data showing**
   - Verify it's Monday (or set TEST_MODE=true)
   - Check yfinance connectivity
   - Verify stock symbols are correct

6. **Hallucination detection failing**
   - Ensure SERPAPI_KEY is valid
   - Check search query formatting
   - Verify network connectivity

### Debug Mode

Enable detailed logging:
```python
# In any module
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Optimization

1. **Database**: Consider PostgreSQL for production
2. **Caching**: Implement Redis for API responses
3. **Charts**: Use CDN for static assets
4. **Email**: Use dedicated email service (SendGrid, SES)

## 📈 Monitoring

### Health Checks

```bash
# Check web service
curl http://localhost:3000/

# Check database
python -c "from storage import init_db; init_db(); print('DB OK')"

# Check disk usage
df -h /data
```

### Logs

- Application logs: `python app.py 2>&1 | tee app.log`
- Cron logs: Check system cron logs or Render dashboard
- Error tracking: Consider Sentry integration

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Style

- Follow PEP 8
- Add type hints
- Document functions
- Write tests for new features

## 📄 License

This project is proprietary software. All rights reserved.

## 🙏 Acknowledgments

- OpenAI for GPT-5
- Anthropic for development assistance
- Perplexity AI for real-time search
- Google for Gemini API
- All news API providers

---

**Built with ❤️ by the NewsAI Team**