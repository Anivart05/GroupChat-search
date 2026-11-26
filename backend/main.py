"""FastAPI server: search API + static web dashboard.

Run from the repo root:
    python -m uvicorn main:app --app-dir backend --port 8001
"""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from benchmark import run_benchmark
from search_engine import SearchEngine

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

messages = json.loads((DATA / "chat_messages.json").read_text(encoding="utf-8"))
test_queries = json.loads((DATA / "test_queries.json").read_text(encoding="utf-8"))
engine = SearchEngine(messages)

app = FastAPI(title="Search a Group Chat Properly", version="1.0.0")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=300)
    top_k: int = Field(5, ge=1, le=20)
    context_window: int = Field(3, ge=0, le=10)
    sender: str | None = None
    month: int | None = Field(None, ge=1, le=12)


@app.post("/api/search")
def search(req: SearchRequest):
    return engine.search(req.query, req.top_k, req.context_window, req.sender, req.month)


@app.get("/api/meta")
def meta():
    return {
        "total_messages": len(engine.messages),
        "participants": engine.participants,
        "first_message": engine.messages[0]["timestamp"],
        "last_message": engine.messages[-1]["timestamp"],
    }


@app.get("/api/benchmark")
def benchmark():
    return run_benchmark(engine, test_queries)


app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
