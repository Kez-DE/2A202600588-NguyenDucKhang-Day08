"""FastAPI wrapper for the RAG chatbot."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.task10_generation import generate_with_citation


app = FastAPI(
    title="Drug Law RAG API",
    description="API cho RAG chatbot trả lời có citation về pháp luật ma túy và tin tức liên quan.",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=10)
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    retrieval_source: str
    sources: list[dict[str, Any]]


def _with_history(question: str, history: list[dict[str, str]]) -> str:
    if not history:
        return question
    turns = []
    for item in history[-8:]:
        role = item.get("role", "user")
        content = item.get("content", "")
        if content:
            turns.append(f"{role}: {content}")
    return "Lịch sử hội thoại:\n" + "\n".join(turns) + f"\n\nCâu hỏi hiện tại: {question}"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = generate_with_citation(
        _with_history(request.question, request.history),
        top_k=request.top_k,
    )
    return ChatResponse(
        answer=result["answer"],
        retrieval_source=result.get("retrieval_source", "unknown"),
        sources=result.get("sources", []),
    )
