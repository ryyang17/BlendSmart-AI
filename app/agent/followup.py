"""Follow-up node — asks the user a targeted clarifying question."""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.agent.state import AgentState
from app.config import settings

_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url)

_SYSTEM = SystemMessage(content=(
    "Je bent BlendSmart AI, een smoothie- en voedingsassistent. "
    "De vraag van de gebruiker is te vaag. "
    "Stel precies één gerichte vervolgvraag om te begrijpen wat de gebruiker nodig heeft. "
    "Vraag naar doelen, dieetwensen, of beschikbare ingrediënten."
))


def run(state: AgentState) -> AgentState:
    last_user = next(
        (m.content for m in reversed(state["messages"]) if m.type == "human"),
        "",
    )
    question = _llm.invoke([_SYSTEM, HumanMessage(content=last_user)]).content
    return {
        "messages": [AIMessage(content=question)],
        "final_answer": question,
    }
