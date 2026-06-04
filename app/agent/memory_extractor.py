"""Memory extractor — regex-based extraction of user preferences from Dutch text."""
import re
from app.memory import profile as profile_store

# ── Name ────────────────────────────────────────────────────────────────────
# (?i:...) makes only the keyword part case-insensitive; [A-Z] still requires
# a true capital, filtering out adjectives like "veganistisch".
# Second fallback: "ik heet" is unambiguous enough to also accept all-lowercase.
_NAME_PATTERNS = [
    r"(?i:mijn\s+naam\s+is\s+)([A-Z][a-z]+)",
    r"(?i:ik\s+heet\s+)([A-Z][a-z]+)",
    r"(?i:ik\s+heet\s+)([a-z]+)",           # all-lowercase fallback ("ik heet ruyi")
]

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

# ── Allergies ────────────────────────────────────────────────────────────────
_ALLERGY_PATTERNS = [
    r"allergisch\s+voor\s+([^.!?]+)",
    r"intolerant\s+voor\s+([^.!?]+)",
    r"ik\s+verdraag\s+([^.!?]+?)\s+niet",
    r"([^.!?,]+?)-?intolerantie",
    r"([^.!?,]+?)-?allergie",
]

# ── Keyword-based dietary preferences ────────────────────────────────────────
_PREF_KEYWORDS: dict[str, str] = {
    "veganistisch": "veganistisch",
    "vegan": "veganistisch",
    "vegetarisch": "vegetarisch",
    "suikervrij": "suikervrij",
    "glutenvrij": "glutenvrij",
    "lactosevrij": "lactosevrij",
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
    """Inline (?i:...) handles keyword matching; captured group stays case-aware."""
    for pat in _NAME_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
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

    return updates


def extract_and_save(session_id: str, user_message: str) -> None:
    """Called in a background thread — extracts profile updates and saves to disk."""
    updates = _extract(user_message)
    if not updates:
        return
    current = profile_store.load(session_id)
    merged = profile_store.merge(current, updates)
    profile_store.save(session_id, merged)
