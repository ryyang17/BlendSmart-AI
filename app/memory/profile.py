"""Persistent user profile — stored as JSON per session_id in data/profiles/."""
import json
from pathlib import Path

_PROFILES_DIR = Path("data/profiles")

_EMPTY: dict = {
    "name": None,
    "allergies": [],
    "preferences": [],
    "goals": [],
    "favorite_ingredients": [],
    "disliked_ingredients": [],
    "available_ingredients": [],
}


def _path(session_id: str) -> Path:
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return _PROFILES_DIR / f"{session_id}.json"


def load(session_id: str) -> dict:
    p = _path(session_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(_EMPTY)


def save(session_id: str, profile: dict) -> None:
    _path(session_id).write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def merge(existing: dict, updates: dict) -> dict:
    """Merge extracted updates into the existing profile. Lists are unioned; name is overwritten."""
    result = dict(existing)
    if updates.get("name"):
        result["name"] = updates["name"]
    for key in ("allergies", "preferences", "goals", "favorite_ingredients", "disliked_ingredients", "available_ingredients"):
        new_items = updates.get(key) or []
        if new_items:
            result[key] = list(dict.fromkeys((result.get(key) or []) + new_items))
    return result
