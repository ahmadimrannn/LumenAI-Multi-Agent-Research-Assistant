from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from config.settings import EXCLUDE_DOMAINS

load_dotenv()

def invoke_tavily(query: str):
  tavily = TavilySearch(
    max_results=10, 
    search_depth="advanced",
    exclude_domains=EXCLUDE_DOMAINS,
  )
  response = tavily.invoke({"query": query})

  return response.get("results", [])