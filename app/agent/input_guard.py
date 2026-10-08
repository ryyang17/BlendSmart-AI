"""Input guard (mitigatie M2b) — deterministic check before the model sees a message.

A 7B model does not reliably resist "negeer je instructies"-style prompts, so obvious
persona-override and prompt-extraction attempts are caught in code. This is a first
line of defence, not a complete one: unusual phrasings can still get through.
"""
import base64
import codecs
import re
import unicodedata

_REFUSAL_HEAD = "Dat kan ik niet doen: ik blijf Smoothie Buddy 🥤 en deel mijn instructies niet. "
_REFUSAL_TAIL = (
    "Zal ik een lekkere smoothie voor je bedenken? Vertel me bijvoorbeeld wat je doel is "
    "(meer energie, beter slapen, ...) of welke ingrediënten je in huis hebt."
)
REFUSAL = _REFUSAL_HEAD + _REFUSAL_TAIL


def refusal_for(profile: dict | None) -> str:
    """Refusal that also confirms the saved allergies/dislikes, so the user sees they still apply."""
    profile = profile or {}
    notes = []
    if profile.get("allergies"):
        notes.append(f"Ik houd rekening met je allergie voor {', '.join(profile['allergies'])}: "
                     "ik maak dus nooit een recept met die ingrediënten.")
    if profile.get("disliked_ingredients"):
        notes.append(f"Ik laat ook {', '.join(profile['disliked_ingredients'])} weg, want dat vind je niet lekker.")
    return _REFUSAL_HEAD + (" ".join(notes) + " " if notes else "") + _REFUSAL_TAIL


_PATTERNS = [
    # "negeer alle voorgaande instructies", "NEGEER AL JE REGELS", "ignore previous instructions"
    r"\b(negeer|negeren|vergeet|ignore|disregard)\b[^.!?]{0,40}\b(instructies|regels|opdrachten|instructions|rules|prompt)\b",
    # persona override: "je bent vanaf nu ...", "vanaf nu ben je ...", "zonder regels"
    r"\bje\s+bent\s+vanaf\s+nu\b",
    r"\bvanaf\s+nu\s+ben\s+je\b",
    r"\bzonder\s+(regels|beperkingen|restricties)\b",
    # prompt extraction
    r"\b(herhaal|toon|geef|print|laat\s+zien|kopieer|citeer)\b[^.!?]{0,60}\b(system|systeem)[\s-]*(prompt|instructies|bericht)\b",
    r"\b(woordelijke?\s+kopie|letterlijk)\b[^.!?]{0,40}\b(system|systeem)[\s-]*(prompt|instructies)\b",
    r"\b(system|systeem)[\s-]*(prompt|instructies)\b[^.!?]{0,40}\b(woordelijk|letterlijk|herhaal)",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


_INVISIBLE = re.compile(r"[​-‏⁠⁦-⁩﻿­]")
# Cyrillic/Greek lookalikes that NFKC leaves alone
_CONFUSABLES = str.maketrans("асеорхуіјѕԁԛѵаеіоρυνκτ", "aceopxyijsdqvaeiopyvkt")
_LEET = str.maketrans("013457@$", "oieastas")
_SPACED = re.compile(r"\b(?:\w[\s.\-_*|]+){3,}\w\b")
_B64 = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


def _variants(message: str) -> list[str]:
    """The message as typed, plus de-obfuscated forms an attacker may use to dodge the regexes."""
    text = unicodedata.normalize("NFKC", message)
    text = _INVISIBLE.sub("", text).translate(_CONFUSABLES)
    variants = [message, text]
    despaced = _SPACED.sub(lambda m: re.sub(r"[\s.\-_*|]+", "", m.group()), text)
    variants.append(despaced)
    variants.append(despaced.translate(_LEET))
    variants.append(codecs.decode(text, "rot13"))
    for token in _B64.findall(text):
        try:
            decoded = base64.b64decode(token + "=" * (-len(token) % 4), validate=True).decode("utf-8")
        except ValueError:
            continue
        if decoded.isprintable():
            variants.append(decoded)
    return variants


def is_injection(message: str) -> bool:
    return any(p.search(v) for v in _variants(message) for p in _COMPILED)
