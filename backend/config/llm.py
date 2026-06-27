from dotenv import load_dotenv
from langchain_groq import ChatGroq
from config.settings import LLM_MODEL_NAME

load_dotenv()

llm = ChatGroq(
  model_name=LLM_MODEL_NAME,
  temperature=0,
  max_tokens=8192
)
