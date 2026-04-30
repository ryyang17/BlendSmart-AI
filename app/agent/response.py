"""Response node — formats and returns the final answer with a disclaimer."""
from app.agent.state import AgentState

DISCLAIMER = (
    "\n\n⚠️ *Dit is algemene voedingsinformatie ter inspiratie, geen medisch advies.*"
)


def run(state: AgentState) -> AgentState:
    # TODO: format state["final_answer"] and append DISCLAIMER
    raise NotImplementedError
