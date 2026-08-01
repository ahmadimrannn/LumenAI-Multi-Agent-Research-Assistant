from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import GEMINI_LLM_MODEL_NAME
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
  model=GEMINI_LLM_MODEL_NAME,
  api_key=GEMINI_API_KEY,
  temperature=0,
)
