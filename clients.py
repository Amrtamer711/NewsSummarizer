from openai import OpenAI
from config import OPENAI_API_KEY, GOOGLE_API_KEY
import google.generativeai as genai

from google import genai
from google.genai import types

# Configure the client
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)


# Configure OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

