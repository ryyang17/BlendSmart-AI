"""Memory extractor — runs in a background thread after the response is sent."""
import json
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.memory import profile as profile_store

_llm = ChatOllama(
    model=settings.ollama_llm_model,
    base_url=settings.ollama_base_url,
    temperature=0,
)

_SYSTEM = SystemMessage(content=(
    "Analyseer het bericht van de gebruiker. Extraheer persoonlijke informatie die expliciet wordt genoemd. "
    "Geef ALLEEN een JSON-object terug met velden die daadwerkelijk vermeld zijn:\n"
    '- "name": naam als de gebruiker zichzelf voorstelt (bijv. "Ik ben Tom", "Ik heet Sara")\n'
    '- "allergies": lijst van allergieën of intoleranties (bijv. ["lactose", "noten"])\n'
    '- "preferences": lijst van dieetvoorkeuren (bijv. ["veganistisch", "suikervrij"])\n'
    '- "goals": lijst van gezondheidsdoelen (bijv. ["meer energie", "gewichtsverlies"])\n'
    '- "favorite_ingredients": ingrediënten die ze lekker vinden\n'
    '- "disliked_ingredients": ingrediënten die ze willen vermijden\n'
    "Geef {} terug als er niets persoonlijks is. Geen uitleg, alleen JSON."
))


def extract_and_save(session_id: str, user_message: str) -> None:
    """Called in a background thread — extracts profile updates and saves to disk."""
    try:
        raw = _llm.invoke([_SYSTEM, HumanMessage(content=user_message)]).content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        updates = json.loads(raw)
    except Exception:
        return

    if not updates:
        return

    current = profile_store.load(session_id)
    merged = profile_store.merge(current, updates)
    profile_store.save(session_id, merged)
