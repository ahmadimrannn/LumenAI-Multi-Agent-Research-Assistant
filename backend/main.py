from fastapi import FastAPI
from executor import graph_executor
from executor import resume_graph
from pydantic import BaseModel
from fastapi import HTTPException
import uuid

app = FastAPI()

class ResearchRequest(BaseModel):
  query: str

class ResumeRequest(BaseModel):
  thread_id: str
  action: str
  edited_query: str | None = None


@app.post("/research")
def get_findings(request: ResearchRequest):
  if not request.query.strip():
    raise HTTPException(status_code=400, detail=f"Can't fetch results without a query.")
  
  thread_id = str(uuid.uuid4()) 
  try:
    response = graph_executor(
      query=request.query, 
      thread_id=thread_id
    )
    return response
  
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Can't fetch results {str(e)}")
  
@app.post("/research/resume")
def resume(request: ResumeRequest):
  
  if request.action not in {"approve", "reject", "edit"}:
    raise HTTPException(
      status_code=400,
      detail="Invalid Action"
    )
  
  if request.action == "edit" and (
    request.edited_query is None or not request.edited_query.strip()
  ):
    raise HTTPException(
      status_code=400,
      detail="edited_query is required when action = 'edit'."
    )
  

  try:
    result = resume_graph(
      action=request.action,
      thread_id=request.thread_id,
      edited_query=request.edited_query
    )

    return result

  except Exception as e:
    raise HTTPException(
      status_code=400,
      detail=f"Can't fetch results: {str(e)}"
    )
  
  