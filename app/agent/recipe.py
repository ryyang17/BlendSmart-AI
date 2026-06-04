"""Recipe generator node — produces a concrete smoothie recipe from retrieved context."""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.state import AgentState
from app.config import settings

_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url)


def _profile_context(profile: dict) -> str:
    lines = []
    if profile.get("name"):
        lines.append(f"De gebruiker heet {profile['name']}.")
    if profile.get("allergies"):
        lines.append(f"Allergieën/intoleranties: {', '.join(profile['allergies'])}.")
    if profile.get("preferences"):
        lines.append(f"Dieetvoorkeuren: {', '.join(profile['preferences'])}.")
    if profile.get("goals"):
        lines.append(f"Gezondheidsdoelen: {', '.join(profile['goals'])}.")
    if profile.get("favorite_ingredients"):
        lines.append(f"Favoriete ingrediënten: {', '.join(profile['favorite_ingredients'])}.")
    if profile.get("disliked_ingredients"):
        lines.append(f"Vermijd: {', '.join(profile['disliked_ingredients'])}.")
    return "\n".join(lines)


def _available_context(profile: dict, state_available: list[str]) -> str:
    """Combine profile-persisted + current-turn available ingredients."""
    combined = list(dict.fromkeys(
        (profile.get("available_ingredients") or []) + (state_available or [])
    ))
    if not combined:
        return ""
    return f"De gebruiker heeft de volgende ingrediënten in huis: {', '.join(combined)}. Gebruik deze zoveel mogelijk in het recept."


def run(state: AgentState) -> AgentState:
    context = "\n\n".join(state.get("retrieved_docs") or [])
    profile = state.get("user_profile") or {}
    profile_section = _profile_context(profile)
    available = state.get("available_ingredients") or []
    available_section = _available_context(profile, available)

    system = SystemMessage(content=(
        "Je bent Blendi 🥤, de vrolijke smoothie-buddy van BlendSmart. "
        "Je spreekt warm, enthousiast en persoonlijk — gebruik af en toe voedingsemoji's (🍌🍓🥬🫚✨). "
        "Moedig de gebruiker altijd aan. "
        "Gebruik de onderstaande voedingsinformatie om een concreet recept of advies te geven. "
        "Geef ingrediënten met hoeveelheden en korte bereidingsstappen. "
        "Houd rekening met alle eerdere berichten in het gesprek, zoals genoemde ingrediënten of wensen. "
        + (f"Pas het recept aan op het profiel van de gebruiker:\n{profile_section}\n\n" if profile_section else "")
        + (f"\n{available_section}\n" if available_section else "")
        + "Vermeld altijd de geschatte calorieën (kcal) van het recept aan het einde van de ingrediëntenlijst, "
        "bijvoorbeeld: '📊 Geschatte calorieën: ~230 kcal per portie'.\n"
        "Antwoord in het Nederlands.\n\n"
        f"Voedingscontext:\n{context}"
    ))
    result = _llm.invoke([system, *state["messages"]])
    return {"final_answer": result.content}
