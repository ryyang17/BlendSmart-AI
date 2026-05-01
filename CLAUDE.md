# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

BlendSmart AI is a local, privacy-first nutrition chatbot built with FastAPI, LangGraph, Ollama, ChromaDB, and Streamlit. Keep the system local by default — avoid cloud APIs or internet-dependent dependencies unless explicitly requested.

The app provides general nutritional information for inspiration only, not medical advice.

## Commands

```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ingest data into ChromaDB (required before first run)
python scripts/ingest.py

# Start backend API
uvicorn app.main:app --reload         # http://localhost:8000

# Start Streamlit frontend (separate terminal)
streamlit run app/frontend/chat.py    # http://localhost:8501

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_agent_graph.py
```

Ollama must be running before the app starts. Pull required models once:
```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

## Agent Graph Architecture

The agent is a **LangGraph state machine** defined in `app/agent/graph.py` with this flow:

```
intent ──[needs_followup=True]──► followup ──► END
   │
   └──[needs_followup=False]──► retriever ──► recipe ──► quality
                                                             │
                                          [quality_ok=False]─┘ (retry retriever)
                                                             │
                                          [quality_ok=True]──► response ──► END
```

**State shape** (`app/agent/state.py` — `AgentState` TypedDict):
- `messages`: conversation history as LangChain Message objects
- `intent`: `"recipe"` | `"info"` | `"unknown"` | `None`
- `retrieved_docs`: list of document strings from ChromaDB
- `needs_followup`: `True` when query is vague (< 4 words)
- `quality_ok`: `True` when answer length ≥ 80 chars (set by quality node)
- `final_answer`: the string sent back to the user

Each node is stateless — all context flows through `AgentState`. The quality node creates a **retry loop**: if the answer is too short, execution goes back to `retriever`, not the start.

## Session Memory

`app/api/chat.py` stores conversation history in an in-memory dict (`_SESSION_HISTORY`) keyed by `session_id`. History resets on app restart — there is no persistent session storage. The chat endpoint accepts `session_id`, `message`, and `history`.

## Data & Ingestion

`scripts/ingest.py` reads `.json`, `.md`, and `.txt` files from `data/nutrients/`, `data/recipes/`, and `data/adh/`, then embeds them via the Ollama API (`nomic-embed-text`) and upserts into ChromaDB. The vector store lives at the path configured in `app/config.py` (defaults to `data/chroma_db/`). The collection is named `blendsmart`.

`app/db/vector_store.py` wraps ChromaDB with a single `query(embedding, top_k)` method that returns document strings.

## Configuration

`app/config.py` uses Pydantic `BaseSettings` loading from `.env`. Key settings: Ollama base URL and model names, ChromaDB path, retrieval `top_k`, quality threshold (min answer length).

## Working Rules

- Make changes as small and local as possible.
- Prefer the existing architecture and file layout in `app/`, `data/`, `scripts/`, and `tests/`.
- When changing behavior, inspect the nearest implementation and the related test first.
- If you change agent flow, retrieval, or response formatting, validate the affected path with `pytest tests/test_agent_graph.py` before expanding scope.
- Update documentation when setup, commands, or user-facing behavior changes.
