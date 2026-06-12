"""Intent classifier node — regex-based, no LLM call needed."""
import re
from app.agent.state import AgentState

# Explicit recipe/drink request
_RECIPE = re.compile(
    r'\b(recept|smoothie|maak|blend|mixen|mix|bereid|shake|drank|drankje|sap)\b',
    re.IGNORECASE,
)

# Explicit information/knowledge request
_INFO = re.compile(
    r'\b(waarom|voedingswaarde|calorie|calorieën|eiwit|eiwitten|vitamine|vitamines|'
    r'mineraal|mineralen|hoeveel|verschil|helpt|werkt|goed\s+voor|beter\s+voor|'
    r'uitleg|meer\s+over|wat\s+doet|wat\s+is|leg\s+uit)\b',
    re.IGNORECASE,
)

# Feeling/goal expressions that implicitly ask for a recipe/solution
_IMPLICIT_RECIPE = re.compile(
    # "ik voel me [anything]"
    r'\bvoel\s+me\b'
    # "ik ben (altijd/steeds) moe/gestrest/..."
    r'|\b(ben|ben\s+altijd|ben\s+steeds)\s+'
    r'(moe|vermoeid\w*|uitgeput|energieloos|futloos|slap|gestrest|gestresst|'
    r'verkouden|zwak|down|ziek|opgebrand)\b'
    # "ik slaap slecht / niet goed"
    r'|\bslaap\s+(slecht|niet\s+goed|heel\s+slecht)\b'
    # "ik heb weinig/geen energie/zin/kracht"
    r'|\bheb\s+(weinig|geen|te\s+weinig)\s+(energie|zin|kracht)\b'
    # "ik heb stress / hoofdpijn / last van ..."
    r'|\bheb\s+(last\s+van|last|hoofdpijn|buikpijn|stress|veel\s+stress)\b'
    # "altijd moe / altijd een dip"
    r'|\baltijd\s+(moe|vermoeid|een\s+dip|honger|trek)\b'
    # explicit goals: "ik wil meer energie / beter slapen / afvallen / ..."
    r'|\bwil\s+(meer\s+energie|beter\s+slapen|afvall?\w*|spieren\s+opbouwen|'
    r'gezonder\s+(eten|leven)|fitter\s+worden|gewicht\s+verliezen|beter\s+eten)\b',
    re.IGNORECASE,
)

# Keywords that signal specificity — stem-based (no trailing \b so derived forms match too)
_SPECIFIC_KW = re.compile(
    r'\b(energie\w*|energiek|moe|vermoeid\w*|slaap\w*|rust|kracht|spier\w*|detox\w*|'
    r'reinig\w*|immuun|weerstand|afvall?\w*|gewicht|ontspann?\w*|concentrat\w*|'
    r'sport\w*|training|herstel|ochtend|ontbijt|stress\w*|verkouden|uitgeput\w*|'
    r'futloos|opgebrand)',
    re.IGNORECASE,
)

# Structural markers: "met X", "voor X", "van X", "zonder X"
_STRUCTURAL = re.compile(r'\b(met|van|voor|zonder)\b\s+\w', re.IGNORECASE)


def run(state: AgentState) -> AgentState:
    last_user = next(
        (m.content for m in reversed(state["messages"]) if m.type == "human"), ""
    )

    if _RECIPE.search(last_user):
        intent = "recipe"
    elif _IMPLICIT_RECIPE.search(last_user):
        intent = "recipe"
    elif _INFO.search(last_user):
        intent = "info"
    else:
        intent = "unknown"

    user_profile = state.get("user_profile") or {}
    profile_has_context = bool(
        user_profile.get("goals")
        or user_profile.get("preferences")
        or user_profile.get("favorite_ingredients")
        or user_profile.get("available_ingredients")
    )
    query_is_specific = bool(
        _SPECIFIC_KW.search(last_user)
        or _STRUCTURAL.search(last_user)
        or _IMPLICIT_RECIPE.search(last_user)
    )

    needs_followup = (
        # Truly vague: unknown intent AND nothing specific in the query
        (intent == "unknown" and not query_is_specific)
        # Short AND generic (short + specific = still actionable)
        or (len(last_user.split()) < 4 and not query_is_specific)
        # Clear intent but no context anywhere
        or (intent in ("recipe", "info") and not query_is_specific and not profile_has_context)
    )
    return {"intent": intent, "needs_followup": needs_followup}
