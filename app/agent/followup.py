"""Follow-up node — asks the user a targeted clarifying question."""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.agent.state import AgentState
from app.config import settings

_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url)

_SYSTEM = SystemMessage(content=(
    "Je bent Blendi 🥤, de vrolijke smoothie-buddy van BlendSmart. "
    "De vraag van de gebruiker is te vaag. "
    "Stel precies één gerichte vervolgvraag om te begrijpen wat de gebruiker nodig heeft. "
    "Vraag naar doelen, dieetwensen, of beschikbare ingrediënten. "
    "Houd je toon warm en uitnodigend."
))


def run(state: AgentState) -> AgentState:
    question = _llm.invoke([_SYSTEM, *state["messages"]]).content
    return {
        "messages": [AIMessage(content=question)],
        "final_answer": question,
    }
