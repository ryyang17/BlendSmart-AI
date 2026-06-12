"""Recipe generator node — produces a concrete smoothie recipe from retrieved context."""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.state import AgentState
from app.config import settings

_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url)

_PREF_RULES: dict[str, str] = {
    "veganistisch": "geen dierlijke producten (geen vlees, vis, zuivel, eieren, honing)",
    "vegetarisch": "geen vlees of vis",
    "lactosevrij": "geen melk, kaas, yoghurt, room of andere zuivelproducten",
    "notenvrij": "absoluut geen noten, pindakaas of notenmelk (ook niet als alternatief)",
    "glutenvrij": "geen gluten (geen tarwe, rogge, gerst of gewone haver)",
    "suikervrij": "geen toegevoegde suiker of zoetstoffen op suikerbasis",
    "keto": "zeer weinig koolhydraten, veel vet",
    "paleo": "geen granen, peulvruchten of zuivel",
    "diabetes": "geen snelle suikers, lage glycemische index",
}


def _profile_context(profile: dict) -> str:
    lines = []
    if profile.get("name"):
        lines.append(f"De gebruiker heet {profile['name']}.")
    if profile.get("allergies"):
        lines.append(
            f"ALLERGIE/INTOLERANTIE (verplicht vermijden): {', '.join(profile['allergies'])}. "
            "Gebruik NOOIT ingrediënten die deze stoffen bevatten."
        )
    if profile.get("preferences"):
        restrictions = []
        for pref in profile["preferences"]:
            rule = _PREF_RULES.get(pref)
            restrictions.append(f"{pref} ({rule})" if rule else pref)
        lines.append(
            f"DIEETVOORKEUR (strikt volgen): {', '.join(restrictions)}. "
            "Gebruik NOOIT ingrediënten die hiermee in strijd zijn."  
        )
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
    return (
        f"De gebruiker heeft alleen de volgende ingrediënten in huis: {', '.join(combined)}.\n"
        "Basisingrediënten die je altijd mag aanvullen zonder melding: water, ijs, zout.\n"
        "Volg deze regels strikt:\n"
        "1. Maak het beste recept dat mogelijk is met alleen deze ingrediënten "
        "(plus de toegestane basisingrediënten).\n"
        "2. Als de ingrediënten onvoldoende zijn voor een volwaardig recept, geef dan "
        "het dichtstbijzijnde alternatief dat WEL volledig werkt met de beschikbare ingrediënten.\n"
        "3. Vermeld ALTIJD aan het einde een sectie '🛒 Wat je nog nodig hebt:' waarin je "
        "exact opsomt welke extra ingrediënten nodig zijn voor het voorgestelde recept "
        "(of schrijf 'Niets! Je hebt alles in huis 🎉' als het recept volledig past).\n"
        "4. Gebruik GEEN ingrediënten die niet in de lijst staan, tenzij het een basisingrediënt is."
    )


def _nutrient_instruction(goals: list[str]) -> str:
    goal_line = (
        f"Leg voor elke stof in één simpele zin uit hoe het helpt bij het doel van de gebruiker ({', '.join(goals)}), "
        "bijv. '→ geeft je meer energie'."
        if goals else
        "Leg voor elke stof in één simpele zin uit wat het voor je doet."
    )
    return (
        "Voeg na de bereidingsstappen altijd een sectie '💊 Voedingsstoffen:' toe. "
        "BELANGRIJK: noem ALLEEN stoffen die expliciet in de voedingscontext hieronder vermeld staan. "
        "Verzin niets en voeg geen stoffen toe die niet in de context staan. "
        "Als de context onvoldoende is voor een specifieke stof, sla die dan over. "
        "Noem 3–5 stoffen met tussen haakjes welke ingrediënten ze leveren. "
        "Schrijf de uitleg in gewone taal, zonder vakjargon — alsof je het aan een vriend uitlegt. "
        + goal_line
        + " Voorbeeld: '- Vitamine C (mango, sinaasappel) → houdt je weerstand op peil'. "
        "Sluit de sectie ALTIJD af met één regel: '📖 Bron: RIVM Voedingsnormen / Voedingscentrum'."
    )


def build_system_message(state: AgentState) -> SystemMessage:
    """Returns the recipe system prompt. Shared with the streaming endpoint."""
    context = "\n\n".join(state.get("retrieved_docs") or [])
    profile = state.get("user_profile") or {}
    profile_section = _profile_context(profile)
    available = state.get("available_ingredients") or []
    available_section = _available_context(profile, available)
    goals = profile.get("goals") or []
    return SystemMessage(content=(
        "Je bent Smoothie Buddy 🥤 — de vrolijke, persoonlijke smoothie-coach van BlendSmart. "
        "Je hebt een warme, enthousiaste en aanmoedigende persoonlijkheid. "
        "Gebruik voedingsemoji's om je berichten levendig te maken (🍌🍓🥬🫚✨💪). "
        "Als de naam van de gebruiker bekend is, gebruik die dan af en toe — spaarzaam en natuurlijk, "
        "niet bij elke zin. "
        "Erken keuzes positief ('Wat een goed idee!', 'Mooie keuze!'). "
        "Sluit elk recept of advies altijd af met één korte, oprechte aanmoedigingsregel, "
        "bijv. 'Geniet ervan! 💪', 'Je bent goed bezig!', 'Wat een geweldige stap richting jouw doel!'. "
        "Gebruik de onderstaande voedingsinformatie om een concreet recept of advies te geven. "
        "Geef ingrediënten met hoeveelheden en korte bereidingsstappen. "
        "Houd rekening met alle eerdere berichten in het gesprek, zoals genoemde ingrediënten of wensen.\n"
        "ALS de gebruiker een gevoel of klacht beschrijft (zoals 'ik ben moe', 'ik slaap slecht', "
        "'ik heb stress'): erken dat kort en empathisch, geef dan direct een passend recept — "
        "leg in één zin uit waarom dit recept helpt bij wat ze beschrijven.\n"
        "TAALREGEL: schrijf altijd in gewone, begrijpelijke taal — alsof je met een vriend praat. "
        "Gebruik GEEN vakjargon of ingewikkelde termen zoals: glycemische index, antioxidanten, "
        "flavonoïden, polyfenolen, oxidatieve stress, metabolisme, macronutriënten, micronutriënten, "
        "ontstekingsremmend, fytonutriënten. "
        "Als zo'n begrip toch nodig is, vervang het door een gewone uitleg "
        "(bijv. niet 'antioxidanten' maar 'stoffen die je cellen beschermen').\n"
        + (f"Houd je STRIKT aan het volgende gebruikersprofiel — dit zijn harde regels, geen suggesties:\n{profile_section}\n\n" if profile_section else "")
        + (f"\n{available_section}\n" if available_section else "")
        + "Vermeld altijd de geschatte calorieën (kcal) van het recept aan het einde van de ingrediëntenlijst, "
        "bijvoorbeeld: '📊 Geschatte calorieën: ~xxx kcal per portie'.\n"
        + _nutrient_instruction(goals) + "\n"
        "Antwoord in het Nederlands.\n\n"
        f"Voedingscontext:\n{context}"
    ))


def run(state: AgentState) -> AgentState:
    system = build_system_message(state)
    result = _llm.invoke([system, *state["messages"]])
    return {"final_answer": result.content}
