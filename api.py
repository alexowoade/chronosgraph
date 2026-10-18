from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from dataclasses import asdict
from agent import ChronosGraphROCmAgent

app = FastAPI(
    title="ChronosGraph REST API",
    description="Temporal Conflict & Stale-Page Web Verification Engine on AMD ROCm",
    version="2.0.0"
)
agent = ChronosGraphROCmAgent()

class RetrieveRequest(BaseModel):
    query: str
    seed_urls: Optional[List[str]] = None

@app.get("/health")
def health():
    return {"status": "ok", "compute_backend": agent.compute_backend}

@app.post("/retrieve")
def retrieve(req: RetrieveRequest):
    result = agent.run_query(query=req.query, seed_urls=req.seed_urls)
    return asdict(result)
