"""LangGraph state machine for the BlendSmart AI agent."""
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent import intent, followup, retriever, recipe, quality, response


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("intent", intent.run)
    graph.add_node("followup", followup.run)
    graph.add_node("retriever", retriever.run)
    graph.add_node("recipe", recipe.run)
    graph.add_node("quality", quality.run)
    graph.add_node("response", response.run)

    graph.set_entry_point("intent")

    graph.add_conditional_edges(
        "intent",
        lambda s: "followup" if s["needs_followup"] else "retriever",
    )
    graph.add_edge("followup", END)
    graph.add_edge("retriever", "recipe")
    graph.add_edge("recipe", "quality")
    graph.add_conditional_edges(
        "quality",
        lambda s: "response" if (s["quality_ok"] or s.get("retry_count", 0) >= 2) else "retriever",
    )
    graph.add_edge("response", END)

    return graph.compile()


agent = build_graph()
