"""Intent classifier node — decides what the user wants and whether we need more context."""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.state import AgentState
from app.config import settings

_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url, temperature=0)

_SYSTEM = SystemMessage(content=(
    "Classify the user's smoothie/nutrition query. "
    "Reply with exactly one word: "
    "'recipe' if they want a smoothie or drink recipe, "
    "'info' if they want nutritional information or health advice, "
    "'unknown' if the query is too vague or completely unrelated."
))


def run(state: AgentState) -> AgentState:
    last_user = next(
        (m.content for m in reversed(state["messages"]) if m.type == "human"),
        "",
    )
    raw = _llm.invoke([_SYSTEM, *state["messages"]]).content.strip().lower()
    intent = raw if raw in {"recipe", "info"} else "unknown"
    needs_followup = intent == "unknown" or len(last_user.split()) < 4
    return {"intent": intent, "needs_followup": needs_followup}
