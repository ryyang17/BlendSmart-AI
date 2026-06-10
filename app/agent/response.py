"""Response node — formats and returns the final answer with a disclaimer."""
from app.agent.state import AgentState

DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Disclaimer:** De informatie die BlendSmart AI verstrekt is uitsluitend bedoeld als "
    "algemene voedingsinformatie ter inspiratie en vervangt geen professioneel medisch of "
    "diëtistisch advies. Raadpleeg altijd een arts of geregistreerde diëtist voor persoonlijk "
    "voedings- of gezondheidsadvies, zeker bij medische aandoeningen, zwangerschap of "
    "specifieke dieetbehoeften."
)


def run(state: AgentState) -> AgentState:
    answer = state.get("final_answer") or ""
    return {"final_answer": answer.strip() + DISCLAIMER}
