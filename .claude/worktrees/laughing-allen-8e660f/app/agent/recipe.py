"""Recipe generator node — produces a concrete smoothie recipe from retrieved context."""
from app.agent.state import AgentState


def run(state: AgentState) -> AgentState:
    # TODO: prompt Ollama with retrieved_docs + user goal to generate a recipe
    raise NotImplementedError
