from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import GEMINI_LLM_MODEL_NAME

load_dotenv()

llm = ChatGoogleGenerativeAI(
  model=GEMINI_LLM_MODEL_NAME,
  temperature=0,
)
