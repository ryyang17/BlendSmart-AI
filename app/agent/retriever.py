"""Retriever node — fetches relevant nutrition documents from ChromaDB."""
from langchain_ollama import OllamaEmbeddings
from app.agent.state import AgentState
from app.config import settings
from app.db import vector_store

_embeddings = OllamaEmbeddings(
    model=settings.ollama_embed_model,
    base_url=settings.ollama_base_url,
)


def run(state: AgentState) -> AgentState:
    user_texts = [m.content for m in state["messages"] if m.type == "human"]
    query = " ".join(user_texts[-4:])
    embedding = _embeddings.embed_query(query)
    docs = vector_store.query(embedding, top_k=settings.retrieval_top_k)
    return {"retrieved_docs": docs}
