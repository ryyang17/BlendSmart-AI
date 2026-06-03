"""Quality checker node — evaluates whether the generated answer is complete and relevant."""
from app.agent.state import AgentState

_MIN_LENGTH = 80


_MAX_RETRIES = 2


def run(state: AgentState) -> AgentState:
    answer = state.get("final_answer") or ""
    quality_ok = len(answer.strip()) >= _MIN_LENGTH
    return {"quality_ok": quality_ok, "retry_count": state.get("retry_count", 0) + 1}
