"""Response node — formats and returns the final answer with a disclaimer."""
from app.agent.state import AgentState

DISCLAIMER = (
    "\n\n💚 *Blendi's tip: dit is algemene voedingsinformatie ter inspiratie, geen medisch advies.*"
)


def run(state: AgentState) -> AgentState:
    answer = state.get("final_answer") or ""
    return {"final_answer": answer.strip() + DISCLAIMER}
