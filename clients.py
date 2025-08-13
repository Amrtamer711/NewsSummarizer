from openai import OpenAI
from config import OPENAI_API_KEY, GOOGLE_API_KEY
import google.generativeai as genai

from google import genai
from google.genai import types

# Configure the client
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)


client = OpenAI(api_key=OPENAI_API_KEY)
# genai.configure(api_key=GOOGLE_API_KEY)
# gemini = genai.GenerativeModel(
#     model_name="gemini-2.5-pro",
#     tools=[Tool(google_search=GoogleSearch())]
# )

