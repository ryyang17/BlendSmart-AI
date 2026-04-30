"""Intent classifier node — decides what the user wants and whether we need more context."""
from app.agent.state import AgentState


def run(state: AgentState) -> AgentState:
    # TODO: call Ollama to classify intent from state["messages"]
    # Set state["intent"] to "recipe" | "info" | "unknown"
    # Set state["needs_followup"] = True when query is too vague
    raise NotImplementedError
