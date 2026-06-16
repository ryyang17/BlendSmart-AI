import json
import threading
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from app.agent.graph import agent
from app.agent import memory_extractor
from app.memory import profile as profile_store
from app.config import settings

_stream_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url)

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


class AvailableIngredientsUpdate(BaseModel):
    items: list[str]


@router.put("/profile/{session_id}/available_ingredients")
def update_available_ingredients(session_id: str, update: AvailableIngredientsUpdate) -> dict:
    prof = profile_store.load(session_id)
    prof["available_ingredients"] = update.items
    profile_store.save(session_id, prof)
    return prof


@router.get("/tip/{session_id}")
async def get_tip(session_id: str):
    """Generates a short personalized daily tip based on the user's profile."""
    from datetime import date
    from langchain_core.messages import HumanMessage, SystemMessage

    user_profile = profile_store.load(session_id)
    name = user_profile.get("name")
    goals = user_profile.get("goals") or []
    available = user_profile.get("available_ingredients") or []
    allergies = user_profile.get("allergies") or []
    favorites = user_profile.get("favorite_ingredients") or []

    # Determine tip type so the frontend can style it
    if goals:
        tip_type = "goal_reminder"
    elif available:
        tip_type = "ingredient_tip"
    else:
        tip_type = "daily_suggestion"

    context_lines = []
    if name:
        context_lines.append(f"De gebruiker heet {name}.")
    if goals:
        context_lines.append(f"Doelen: {', '.join(goals)}.")
    if favorites:
        context_lines.append(f"Lekker vindt: {', '.join(favorites[:4])}.")
    if available:
        context_lines.append(f"In huis: {', '.join(available[:4])}.")
    if allergies:
        context_lines.append(f"Allergieën: {', '.join(allergies)}.")

    today = date.today().strftime("%A %d %B")
    system = SystemMessage(content=(
        "Je bent Smoothie Buddy 🥤 — de vrolijke, persoonlijke smoothie-coach van BlendSmart. "
        "Schrijf een korte, persoonlijke openingsboodschap van precies 1 à 2 zinnen. "
        "Stel één concreet smoothie-idee of tip voor dat past bij het profiel. "
        "Schrijf warm en aanmoedigend, in gewone taal zonder vakjargon. "
        "Gebruik de naam van de gebruiker als die bekend is. "
        "Begin met een enthousiaste begroeting. Gebruik één passende emoji. "
        "Maak het bericht gevarieerd — het is vandaag " + today + ".\n\n"
        + ("\n".join(context_lines) if context_lines else "Geen profielinfo beschikbaar, geef een algemene tip.")
    ))
    result = await _stream_llm.ainvoke([system, HumanMessage(content="Stuur je dagelijkse bericht.")])
    return {"tip": result.content, "type": tip_type}


_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    from app.agent import intent as intent_node, retriever as retriever_node, followup as followup_node
    from app.agent.recipe import build_system_message
    from app.agent.response import DISCLAIMER

    history = _get_history(request.session_id, request.history)
    user_profile = profile_store.load(request.session_id) if request.session_id else {}
    messages = _build_messages(history, request.message)

    base_state = {
        "messages": messages,
        "user_profile": user_profile,
        "available_ingredients": user_profile.get("available_ingredients") or [],
        "retrieved_docs": [],
        "intent": None,
        "needs_followup": False,
        "quality_ok": False,
        "final_answer": None,
        "retry_count": 0,
    }

    # Instant regex intent — no LLM call
    intent_result = intent_node.run(base_state)

    if intent_result["needs_followup"]:
        result = followup_node.run(base_state)
        answer = result.get("final_answer") or "Kun je je vraag wat verduidelijken?"
        _store_turn(request.session_id, history, request.message, answer)
        if request.session_id:
            threading.Thread(
                target=memory_extractor.extract_and_save,
                args=(request.session_id, request.message),
                daemon=True,
            ).start()

        async def _once():
            yield f"data: {json.dumps({'token': answer, 'done': True, 'user_name': user_profile.get('name')})}\n\n"

        return StreamingResponse(_once(), media_type="text/event-stream", headers=_SSE_HEADERS)

    # Retrieval (embedding only — fast)
    ret_result = retriever_node.run({**base_state, "intent": intent_result["intent"]})
    system_msg = build_system_message({**base_state, "retrieved_docs": ret_result.get("retrieved_docs") or []})

    async def generate():
        full_text = ""
        try:
            async for chunk in _stream_llm.astream([system_msg, *messages]):
                token = chunk.content
                if token:
                    full_text += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'token': DISCLAIMER, 'done': True, 'user_name': user_profile.get('name')})}\n\n"
            full_text = full_text.strip() + DISCLAIMER
        finally:
            _store_turn(request.session_id, history, request.message, full_text)
            if request.session_id:
                threading.Thread(
                    target=memory_extractor.extract_and_save,
                    args=(request.session_id, request.message),
                    daemon=True,
                ).start()

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)
