"""Output guard (mitigatie M2c) — deterministic check on the model's reply.

Independent of the language or wording of the attack: if the reply reproduces a run of
words from our own system prompt, it is blocked. The reference text is built from the real
system prompt, so it never drifts out of sync with recipe.py.
"""
import re
import unicodedata
from functools import lru_cache

from app.agent.input_guard import REFUSAL

NGRAM = 8  # consecutive words copied from the prompt that count as a leak
HOLDBACK_WORDS = NGRAM  # streaming: words kept back until they have been checked

_QUOTED = re.compile(r"""'[^']{8,}?'|"[^"]{8,}?\"""")
_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


def _words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).casefold()
    return [w for w in _NON_WORD.split(text) if w]


@lru_cache(maxsize=1)
def _reference_ngrams() -> frozenset:
    from app.agent.recipe import build_system_message

    prompt = build_system_message({}).content
    # Quoted examples ('Vitamine C (mango) → ...') are meant to be imitated, not secret.
    prompt = _QUOTED.sub(" ", prompt)
    words = _words(prompt)
    return frozenset(tuple(words[i:i + NGRAM]) for i in range(len(words) - NGRAM + 1))


def leaks_prompt(reply: str) -> bool:
    words = _words(reply)
    ref = _reference_ngrams()
    return any(tuple(words[i:i + NGRAM]) in ref for i in range(len(words) - NGRAM + 1))


def safe_reply(reply: str) -> str:
    return REFUSAL if leaks_prompt(reply) else reply


def releasable_len(text: str) -> int:
    """Length of the prefix of a streaming reply that is safe to show: everything except
    the last HOLDBACK_WORDS words, which could still turn out to be the end of a leak."""
    starts = [m.start() for m in re.finditer(r"\S+", text)]
    if len(starts) <= HOLDBACK_WORDS:
        return 0
    return starts[-HOLDBACK_WORDS]
