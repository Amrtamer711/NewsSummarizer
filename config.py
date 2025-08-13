from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env

APP_PSWD = os.getenv("APP_PSWD")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_IO_KEY = os.getenv("NEWS_IO_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
