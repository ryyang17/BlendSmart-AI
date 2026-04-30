"""Retriever node — fetches relevant nutrition documents from ChromaDB."""
from app.agent.state import AgentState


def run(state: AgentState) -> AgentState:
    # TODO: embed the latest user message with nomic-embed-text via Ollama
    # and query ChromaDB for top-k relevant chunks
    raise NotImplementedError
