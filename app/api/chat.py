from fastapi import APIRouter
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from app.agent.graph import agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str


def _build_messages(history: list[dict], message: str) -> list:
    msgs = []
    for h in history:
        role = h.get("role", "")
        content = h.get("content", "")
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs.append(AIMessage(content=content))
    msgs.append(HumanMessage(content=message))
    return msgs


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    initial_state = {
        "messages": _build_messages(request.history, request.message),
        "intent": None,
        "retrieved_docs": [],
        "needs_followup": False,
        "quality_ok": False,
        "final_answer": None,
    }
    result = agent.invoke(initial_state)
    reply = result.get("final_answer") or "Er is iets misgegaan. Probeer opnieuw."
    return ChatResponse(reply=reply)
