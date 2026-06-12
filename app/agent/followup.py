"""Follow-up node — asks a targeted clarifying question based on what the profile is missing."""
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, SystemMessage
from app.agent.state import AgentState
from app.config import settings

_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url)


def _build_system(user_profile: dict) -> SystemMessage:
    known, missing = [], []

    if user_profile.get("name"):
        known.append(f"naam: {user_profile['name']}")
    if user_profile.get("goals"):
        known.append(f"doelen: {', '.join(user_profile['goals'])}")
    else:
        missing.append("wat de gebruiker wil bereiken (meer energie, beter slapen, afvallen, etc.)")
    if user_profile.get("preferences"):
        known.append(f"dieet: {', '.join(user_profile['preferences'])}")
    if user_profile.get("allergies"):
        known.append(f"allergieën: {', '.join(user_profile['allergies'])}")
    avail = user_profile.get("available_ingredients") or []
    favs = user_profile.get("favorite_ingredients") or []
    if avail or favs:
        known.append(f"ingrediënten: {', '.join((avail + favs)[:5])}")
    else:
        missing.append("welke ingrediënten beschikbaar zijn of lekker gevonden worden")

    context = ""
    if known:
        context += f"Wat je al weet over de gebruiker: {'; '.join(known)}.\n"
    if missing:
        context += (
            f"Wat ontbreekt voor een goed advies: {'; '.join(missing)}.\n"
            "Stel een vraag die het EERSTE ontbrekende punt helder maakt.\n"
        )

    return SystemMessage(content=(
        "Je bent Smoothie Buddy 🥤 — de vrolijke, persoonlijke smoothie-coach van BlendSmart. "
        "Je toon is warm, enthousiast en uitnodigend. "
        "De vraag heeft te weinig informatie voor een goed recept of advies.\n"
        + context
        + "Stel precies één korte, gerichte vraag — geen opsomming van vragen. "
        "Begin met een positieve of nieuwsgierige opmerking voordat je de vraag stelt, "
        "bijv. 'Oh leuk, vertel me meer!' of 'Dat klinkt goed!'. "
        "Schrijf in gewone, vriendelijke taal zonder vakjargon."
    ))


def run(state: AgentState) -> AgentState:
    user_profile = state.get("user_profile") or {}
    system = _build_system(user_profile)
    question = _llm.invoke([system, *state["messages"]]).content
    return {
        "messages": [AIMessage(content=question)],
        "final_answer": question,
    }
