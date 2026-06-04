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


def run(state: AgentState) -> AgentState:
    context = "\n\n".join(state.get("retrieved_docs") or [])
    profile = state.get("user_profile") or {}
    profile_section = _profile_context(profile)

    system = SystemMessage(content=(
        "Je bent BlendSmart AI, een smoothie- en voedingsassistent. "
        "Gebruik de onderstaande voedingsinformatie om een concreet recept of advies te geven. "
        "Geef ingrediënten met hoeveelheden en korte bereidingsstappen. "
        "Houd rekening met alle eerdere berichten in het gesprek, zoals genoemde ingrediënten of wensen. "
        + (f"Pas het recept aan op het profiel van de gebruiker:\n{profile_section}\n\n" if profile_section else "")
        + "Antwoord in het Nederlands.\n\n"
        f"Voedingscontext:\n{context}"
    ))
    result = _llm.invoke([system, *state["messages"]])
    return {"final_answer": result.content}
