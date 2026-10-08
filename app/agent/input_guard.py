"""Input guard (mitigatie M2b) — deterministic check before the model sees a message.

A 7B model does not reliably resist "negeer je instructies"-style prompts, so obvious
persona-override and prompt-extraction attempts are caught in code. This is a first
line of defence, not a complete one: unusual phrasings can still get through.
"""
import re

REFUSAL = (
    "Dat kan ik niet doen: ik blijf Smoothie Buddy 🥤 en deel mijn instructies niet. "
    "Zal ik een lekkere smoothie voor je bedenken? Vertel me bijvoorbeeld wat je doel is "
    "(meer energie, beter slapen, ...) of welke ingrediënten je in huis hebt."
)

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


def is_injection(message: str) -> bool:
    return any(p.search(message) for p in _COMPILED)
