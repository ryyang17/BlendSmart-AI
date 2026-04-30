"""ChromaDB client and query helpers."""
import chromadb
from app.config import settings

_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_collection():
    return get_client().get_or_create_collection(settings.chroma_collection_name)


def query(embedding: list[float], top_k: int = 5) -> list[str]:
    results = get_collection().query(query_embeddings=[embedding], n_results=top_k)
    return results["documents"][0] if results["documents"] else []
