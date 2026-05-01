"""Load nutrition data and recipes from data/ into ChromaDB."""
import json
import pathlib
import httpx
import sys
from app.config import settings
from app.db.vector_store import get_collection

DATA_DIRS = [
    pathlib.Path("data/nutrients"),
    pathlib.Path("data/recipes"),
    pathlib.Path("data/adh"),
]


def embed(text: str) -> list[float]:
    """Embed text using Ollama. Raises httpx.HTTPError if Ollama is not available."""
    try:
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except httpx.ConnectError as e:
        print(f"❌ ERROR: Cannot connect to Ollama at {settings.ollama_base_url}")
        print(f"   Make sure Ollama is running. Details: {e}")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"❌ ERROR: Ollama returned status {e.response.status_code}")
        print(f"   Details: {e.response.text}")
        sys.exit(1)


def load_documents() -> list[tuple[str, str]]:
    """Return (id, text) pairs from all JSON/Markdown/text files in data/."""
    docs = []
    skipped = []
    
    for directory in DATA_DIRS:
        if not directory.exists():
            print(f"⚠️  Warning: Directory not found: {directory}")
            continue
            
        for path in directory.rglob("*"):
            # Skip directories
            if path.is_dir():
                continue
                
            if path.suffix == ".json":
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    text = json.dumps(data, ensure_ascii=False)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Skipping invalid JSON: {path} ({e})")
                    skipped.append((path.stem, f"Invalid JSON: {e}"))
                    continue
                except Exception as e:
                    print(f"⚠️  Skipping file: {path} ({e})")
                    skipped.append((path.stem, str(e)))
                    continue
            elif path.suffix in (".md", ".txt"):
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception as e:
                    print(f"⚠️  Skipping file: {path} ({e})")
                    skipped.append((path.stem, str(e)))
                    continue
            else:
                continue
                
            docs.append((path.stem, text))
    
    if skipped:
        print(f"\n⚠️  Skipped {len(skipped)} files:")
        for doc_id, reason in skipped:
            print(f"   - {doc_id}: {reason}")
    
    return docs


def main() -> None:
    collection = get_collection()
    docs = load_documents()
    
    if not docs:
        print("❌ ERROR: No documents found in data/")
        sys.exit(1)
    
    print(f"\n📚 Ingesting {len(docs)} documents...\n")
    
    failed = []
    success_count = 0
    
    for doc_id, text in docs:
        try:
            embedding = embed(text)
            collection.upsert(ids=[doc_id], embeddings=[embedding], documents=[text])
            print(f"  ✓ {doc_id}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ {doc_id}: {e}")
            failed.append((doc_id, str(e)))
    
    print(f"\n✅ Successfully ingested {success_count}/{len(docs)} documents.")
    
    if failed:
        print(f"❌ Failed to ingest {len(failed)} documents:")
        for doc_id, reason in failed:
            print(f"   - {doc_id}: {reason}")
        sys.exit(1)
    
    # Verify data in ChromaDB
    try:
        count = collection.count()
        print(f"📊 ChromaDB now contains {count} embeddings.")
    except Exception as e:
        print(f"⚠️  Could not verify ChromaDB count: {e}")


if __name__ == "__main__":
    main()
