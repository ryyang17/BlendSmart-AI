"""Quality checker node — evaluates whether the generated answer is complete and relevant."""
from app.agent.state import AgentState


def run(state: AgentState) -> AgentState:
    # TODO: ask Ollama to score the answer; set state["quality_ok"] accordingly
    raise NotImplementedError
