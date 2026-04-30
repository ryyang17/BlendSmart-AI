"""Load nutrition data and recipes from data/ into ChromaDB."""
import json
import pathlib
import httpx
from app.config import settings
from app.db.vector_store import get_collection

DATA_DIRS = [
    pathlib.Path("data/nutrients"),
    pathlib.Path("data/recipes"),
    pathlib.Path("data/adh"),
]


def embed(text: str) -> list[float]:
    resp = httpx.post(
        f"{settings.ollama_base_url}/api/embeddings",
        json={"model": settings.ollama_embed_model, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def load_documents() -> list[tuple[str, str]]:
    """Return (id, text) pairs from all JSON/Markdown files in data/."""
    docs = []
    for directory in DATA_DIRS:
        for path in directory.rglob("*"):
            if path.suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                text = json.dumps(data, ensure_ascii=False)
            elif path.suffix in (".md", ".txt"):
                text = path.read_text(encoding="utf-8")
            else:
                continue
            docs.append((path.stem, text))
    return docs


def main() -> None:
    collection = get_collection()
    docs = load_documents()
    print(f"Ingesting {len(docs)} documents...")
    for doc_id, text in docs:
        embedding = embed(text)
        collection.upsert(ids=[doc_id], embeddings=[embedding], documents=[text])
        print(f"  ✓ {doc_id}")
    print("Done.")


if __name__ == "__main__":
    main()
