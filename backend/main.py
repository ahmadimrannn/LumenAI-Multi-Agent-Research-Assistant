from fastapi import FastAPI
from executor import graph_executor
from pydantic import BaseModel
from fastapi import HTTPException

app = FastAPI()

class ResearchRequest(BaseModel):
  query: str


@app.post("/research")
async def get_findings(request: ResearchRequest):
  if not request.query:
    raise HTTPException(status_code=400, detail=f"Can't fetch results without a query.")
  
  try:
    response = await graph_executor(request.query)
    return response
  
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Can't fetch results {str(e)}")
  
  