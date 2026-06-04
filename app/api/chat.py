import threading
from fastapi import APIRouter
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from app.agent.graph import agent
from app.agent import memory_extractor
from app.memory import profile as profile_store

router = APIRouter()

_SESSION_HISTORY: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    user_name: str | None = None


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


def _get_history(session_id: str | None, history: list[dict]) -> list[dict]:
    if not session_id:
        return history

    if history:
        _SESSION_HISTORY[session_id] = list(history)
        return history

    return _SESSION_HISTORY.get(session_id, [])


def _store_turn(session_id: str | None, history: list[dict], message: str, reply: str) -> None:
    if not session_id:
        return

    _SESSION_HISTORY[session_id] = [
        *history,
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    history = _get_history(request.session_id, request.history)
    user_profile = profile_store.load(request.session_id) if request.session_id else {}
    initial_state = {
        "messages": _build_messages(history, request.message),
        "intent": None,
        "retrieved_docs": [],
        "needs_followup": False,
        "quality_ok": False,
        "final_answer": None,
        "retry_count": 0,
        "user_profile": user_profile,
        "available_ingredients": user_profile.get("available_ingredients") or [],
    }
    result = agent.invoke(initial_state)
    reply = result.get("final_answer") or "Er is iets misgegaan. Probeer opnieuw."
    _store_turn(request.session_id, history, request.message, reply)

    if request.session_id:
        threading.Thread(
            target=memory_extractor.extract_and_save,
            args=(request.session_id, request.message),
            daemon=True,
        ).start()

    current_name = user_profile.get("name")
    return ChatResponse(reply=reply, user_name=current_name)


@router.get("/profile/{session_id}")
def get_profile(session_id: str) -> dict:
    return profile_store.load(session_id)
