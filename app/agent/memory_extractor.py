"""Memory extractor — regex-based extraction of user preferences from Dutch text."""
import re
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from app.config import settings
from app.memory import profile as profile_store

_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url)

# ── Name ────────────────────────────────────────────────────────────────────
# Unambiguous phrases accept any case; "ik ben" keeps [A-Z] to avoid matching
# adjectives like "allergisch". _first_name() filters a blacklist + capitalizes.
_NAME_PATTERNS = [
    r"(?i:mijn\s+naam\s+is\s+)([A-Za-z]+)",   # "mijn naam is ruyi" / "Mijn naam is Ruyi"
    r"(?i:ik\s+heet\s+)([A-Za-z]+)",            # "ik heet ruyi" / "Ik heet Ruyi"
    r"(?i:noem\s+me\s+)([A-Za-z]+)",            # "noem me ruyi"
    r"(?i:ik\s+ben\s+)([A-Z][a-z]+)",           # "Ik ben Ruyi" — capital still required (less specific)
]

# Words that could be captured by "ik ben X" but are not names
_NON_NAMES = frozenset({
    "moe", "fit", "ziek", "blij", "bang", "druk", "klaar", "beter", "goed",
    "allergisch", "vegan", "diabeet", "keto", "vegetarisch", "sportief",
    "lactosevrij", "glutenvrij", "suikervrij", "notenvrij", "actief", "gezond", "zwanger",
})

# ── Dislikes ─────────────────────────────────────────────────────────────────
# Stop at sentence-ending punctuation only (not commas) so "spinazie en banaan"
# is captured in full; _split_ingredients handles the splitting.
_DISLIKE_PATTERNS = [
    r"ik\s+houd?\s+niet\s+van\s+([^.!?]+)",
    r"ik\s+lust\s+([^.!?]+?)\s+niet",
    r"ik\s+vind\s+([^.!?]+?)\s+niet\s+lekker",
    r"geen\s+([^.!?]+?)\s+(?:voor\s+mij|alsjeblieft|graag)",
    r"ik\s+eet\s+geen\s+([^.!?]+)",
]

# ── Likes ────────────────────────────────────────────────────────────────────
_LIKE_PATTERNS = [
    r"ik\s+houd?\s+van\s+([^.!?]+)",
    r"ik\s+vind\s+([^.!?]+?)\s+lekker",
    r"ik\s+eet\s+graag\s+([^.!?]+)",
    r"ik\s+lust\s+graag\s+([^.!?]+)",
]

# ── Available ingredients (user has at home) ─────────────────────────────────
_AVAILABLE_PATTERNS = [
    r"ik\s+heb\s+([^.!?]+?)\s+in\s+huis",
    r"ik\s+heb\s+thuis\s+([^.!?]+)",
    r"ik\s+heb\s+([^.!?]+?)\s+thuis",
    r"maak\s+iets\s+met\s+([^.!?]+)",
    r"ik\s+heb\s+([^.!?]+?)\s+beschikbaar",
    r"ik\s+heb\s+alleen\s+([^.!?]+)",
    r"gebruik\s+([^.!?]+?)\s+als\s+ingredi[eë]nt",
    r"er\s+staat\s+([^.!?]+?)\s+in\s+(?:mijn\s+)?koelkast",
    r"ik\s+wil\s+iets\s+maken\s+met\s+([^.!?]+)",
]

# ── Allergies ────────────────────────────────────────────────────────────────
# The -intolerantie/-allergie patterns use \b(\w+) so only the substance word
# directly before the suffix is captured — not the whole phrase "ik heb lactose".
_ALLERGY_PATTERNS = [
    r"allergisch\s+voor\s+([^.!?]+)",
    r"intolerant\s+voor\s+([^.!?]+)",
    r"ik\s+verdraag\s+([^.!?]+?)\s+niet",
    r"\b(\w+)\s*-\s*intolerantie",   # "lactose-intolerantie" → "lactose"
    r"\b(\w+)\s+intolerantie",        # "lactose intolerantie" → "lactose"
    r"\b(\w+)\s*-\s*allergie",        # "noten-allergie" → "noten"
    r"\b(\w+)\s+allergie",            # "noten allergie" → "noten"
]

# ── Keyword-based dietary preferences ────────────────────────────────────────
_PREF_KEYWORDS: dict[str, str] = {
    "veganistisch": "veganistisch",
    "vegan": "veganistisch",
    "vegetarisch": "vegetarisch",
    "suikervrij": "suikervrij",
    "glutenvrij": "glutenvrij",
    "lactosevrij": "lactosevrij",
    "notenvrij": "notenvrij",
    "keto": "keto",
    "paleo": "paleo",
    "ik ben diabeet": "diabetes",
}

# ── Goal phrases ──────────────────────────────────────────────────────────────
_GOAL_PHRASES: dict[str, str] = {
    r"meer\s+energie": "meer energie",
    r"afvall?en": "afvallen",
    r"gewicht\s+verliezen": "afvallen",
    r"spieren\s+opbouwen": "spieren opbouwen",
    r"gezonder\s+eten": "gezonder eten",
    r"beter\s+slapen": "beter slapen",
    r"immuunsysteem\s+versterken": "immuunsysteem versterken",
}


def _clean(value: str) -> str:
    return value.strip().rstrip(".,!? ")


def _split_ingredients(raw: str) -> list[str]:
    """Split 'spinazie en banaan' or 'spinazie, banaan en mango' into individual items."""
    parts = re.split(r",\s*|\s+en\s+", raw, flags=re.IGNORECASE)
    return [_clean(p) for p in parts if _clean(p)]


def _first_name(text: str) -> str | None:
    for pat in _NAME_PATTERNS:
        m = re.search(pat, text)
        if m:
            candidate = m.group(1).strip()
            if len(candidate) >= 2 and candidate.lower() not in _NON_NAMES:
                return candidate.capitalize()
    return None


def _all(text: str, patterns: list[str]) -> list[str]:
    results = []
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            results.extend(_split_ingredients(m.group(1)))
    return results


def _extract(message: str) -> dict:
    updates: dict = {}

    name = _first_name(message)
    if name:
        updates["name"] = name

    dislikes = _all(message, _DISLIKE_PATTERNS)
    if dislikes:
        updates["disliked_ingredients"] = dislikes

    likes = _all(message, _LIKE_PATTERNS)
    if likes:
        updates["favorite_ingredients"] = likes

    allergies = _all(message, _ALLERGY_PATTERNS)
    if allergies:
        updates["allergies"] = allergies

    # deduplicate via dict.fromkeys to preserve order
    prefs = list(dict.fromkeys(
        label for kw, label in _PREF_KEYWORDS.items()
        if re.search(r"\b" + re.escape(kw) + r"\b", message, re.IGNORECASE)
    ))
    if prefs:
        updates["preferences"] = prefs

    goals = [label for pat, label in _GOAL_PHRASES.items() if re.search(pat, message, re.IGNORECASE)]
    if goals:
        updates["goals"] = goals

    available = _all(message, _AVAILABLE_PATTERNS)
    if available:
        updates["available_ingredients"] = available

    return updates


def _normalize_labels(items: list[str]) -> list[str]:
    """LLM spelling correction for extracted Dutch labels. Runs in the background thread."""
    if not items:
        return items
    try:
        result = _llm.invoke([HumanMessage(content=(
            "Corrigeer alleen de spelling van deze Nederlandse voedingsitems of dieetvoorkeuren. "
            "Gebruik de enkelvoudsvorm (bijv. 'banaan' niet 'bananen'). "
            "Geen uitleg, geen aanvullingen. "
            "Antwoord met exact evenveel items als de input, gescheiden door komma's.\n\n"
            f"Input: {', '.join(items)}\nOutput:"
        ))])
        corrected = [p.strip().rstrip(".,") for p in result.content.split(",") if p.strip()]
        return corrected if len(corrected) == len(items) else items
    except Exception:
        return items


def extract_and_save(session_id: str, user_message: str) -> None:
    """Called in a background thread — extracts profile updates and saves to disk."""
    updates = _extract(user_message)
    if not updates:
        return
    for key in ("favorite_ingredients", "disliked_ingredients", "allergies", "available_ingredients"):
        if key in updates:
            updates[key] = _normalize_labels(updates[key])
    current = profile_store.load(session_id)
    merged = profile_store.merge(current, updates)
    profile_store.save(session_id, merged)
