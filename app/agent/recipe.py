"""Recipe generator node — produces a concrete smoothie recipe from retrieved context."""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.state import AgentState
from app.config import settings

_llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url)


def run(state: AgentState) -> AgentState:
    context = "\n\n".join(state.get("retrieved_docs") or [])
    system = SystemMessage(content=(
        "Je bent BlendSmart AI, een smoothie- en voedingsassistent. "
        "Gebruik de onderstaande voedingsinformatie om een concreet recept of advies te geven. "
        "Geef ingrediënten met hoeveelheden en korte bereidingsstappen. "
        "Houd rekening met alle eerdere berichten in het gesprek, zoals genoemde ingrediënten of wensen. "
        "Antwoord in het Nederlands.\n\n"
        f"Voedingscontext:\n{context}"
    ))
    result = _llm.invoke([system, *state["messages"]])
    return {"final_answer": result.content}
