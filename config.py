from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env

APP_PSWD = os.getenv("APP_PSWD")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_IO_KEY = os.getenv("NEWS_IO_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Outlook/Office 365 SMTP
OUTLOOK_SMTP_HOST = os.getenv("OUTLOOK_SMTP_HOST", "smtp.office365.com")
OUTLOOK_SMTP_PORT = int(os.getenv("OUTLOOK_SMTP_PORT", "587"))
OUTLOOK_SMTP_USER = os.getenv("OUTLOOK_SMTP_USER", "")  # e.g. yourname@yourdomain.com
OUTLOOK_SMTP_PASS = os.getenv("OUTLOOK_SMTP_PASS", "")  # app password or account password if enabled

# Public base URL of the site for links in notifications
BASE_PUBLIC_URL = os.getenv("BASE_PUBLIC_URL", "http://localhost:3000")

# Data directory configuration
# On Render.com, persistent disk is mounted at /data
# Locally, use ./data
DATA_DIR = os.getenv("DATA_DIR", "/data" if os.path.exists("/data") else "./data")
DATABASE_PATH = os.path.join(DATA_DIR, "newsai.db")
STATIC_DIR = os.path.join(DATA_DIR, "static")
