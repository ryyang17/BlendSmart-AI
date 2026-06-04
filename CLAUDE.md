# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

BlendSmart AI is a local, privacy-first nutrition chatbot built with FastAPI, LangGraph, Ollama, and ChromaDB. The frontend is a plain HTML/CSS/JS single-page app served directly by FastAPI. Keep the system local by default — avoid cloud APIs or internet-dependent dependencies unless explicitly requested.

The app provides general nutritional information for inspiration only, not medical advice.

## Commands

```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ingest data into ChromaDB (required before first run)
python scripts/ingest.py

# Start the app (backend + frontend served together)
uvicorn app.main:app --reload   # http://localhost:8000

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

The Streamlit file (`app/frontend/chat.py`) still exists as a legacy fallback but the primary UI is `http://localhost:8000` (served as a static file by FastAPI).

## Agent Graph Architecture

The agent is a **LangGraph state machine** defined in `app/agent/graph.py` with this flow:

```
intent ──[needs_followup=True]──► followup ──► END
   │
   └──[needs_followup=False]──► retriever ──► recipe ──► quality
                                                             │
                                          [quality_ok=False]─┘ (retry retriever, max 2x)
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
- `retry_count`: number of quality retries so far (max 2)
- `user_profile`: persistent user preferences dict (loaded from disk per session)

Each node is stateless — all context flows through `AgentState`. The quality node creates a **retry loop**: if the answer is too short, execution goes back to `retriever`, not the start.

## User Memory System

User preferences are stored persistently as JSON files in `data/profiles/{session_id}.json`. Memory survives app restarts.

**Profile shape:**
```json
{
  "name": "Ruyi",
  "allergies": ["lactose"],
  "preferences": ["veganistisch"],
  "goals": ["meer energie"],
  "favorite_ingredients": ["spinazie", "banaan"],
  "disliked_ingredients": ["komkommer"]
}
```

**How it works:**
1. `app/api/chat.py` loads the profile from disk before invoking the agent and passes it as `user_profile` in the initial state.
2. `app/agent/recipe.py` injects the profile into the system prompt so recipes respect allergies, preferences, and goals.
3. After returning the response to the user, a **background thread** (`threading.Thread`) calls `app/agent/memory_extractor.extract_and_save(session_id, user_message)`.
4. `memory_extractor.py` uses **regex patterns** (no extra LLM call) to detect Dutch phrases like "ik hou niet van X", "ik ben allergisch voor X", "ik heet X" and updates the profile on disk.

The background thread approach means memory extraction never adds latency to the user response.

**Profile endpoint:** `GET /api/profile/{session_id}` — returns the full profile dict.

## Session Memory

`app/api/chat.py` stores conversation history in an in-memory dict (`_SESSION_HISTORY`) keyed by `session_id`. Turn history resets on app restart. User profile preferences (name, allergies, etc.) are persistent via the JSON file system described above.

## Frontend

The primary frontend is `app/frontend/static/index.html` — a single HTML/CSS/JS page served by FastAPI at `http://localhost:8000`. It communicates with the API via `fetch()`.

Interactive elements:
- **Mood board** — 6 clickable cards (Energie, Detox, Kracht, Rust, Immuun, Verrassing) that send preset prompts
- **Quick chips** — shortcut buttons below the input field
- **Profile panel** — slide-in panel showing known name, favorites, dislikes, allergies, dietary preferences, and goals as colored tags
- **Recipe cards** — assistant messages containing recipes are automatically rendered in a distinct card format
- **Personalized greeting** — header and welcome message update with the user's name once detected

`session_id` is stored in `localStorage` so the same profile is loaded on return visits.

## Data & Ingestion

`scripts/ingest.py` reads `.json`, `.md`, and `.txt` files from `data/nutrients/`, `data/recipes/`, and `data/adh/`, then embeds them via the Ollama API (`nomic-embed-text`) and upserts into ChromaDB. The vector store lives at the path configured in `app/config.py` (defaults to `data/chroma_db/`). The collection is named `blendsmart`.

`app/db/vector_store.py` wraps ChromaDB with a single `query(embedding, top_k)` method that returns document strings.

## Configuration

`app/config.py` uses Pydantic `BaseSettings` loading from `.env`. Key settings: Ollama base URL and model names, ChromaDB path, retrieval `top_k`, quality threshold (min answer length).

## Project Structure

```
app/
├── agent/
│   ├── graph.py            # LangGraph state machine
│   ├── state.py            # AgentState TypedDict (includes user_profile)
│   ├── intent.py           # Intent classifier node
│   ├── retriever.py        # ChromaDB retrieval node
│   ├── followup.py         # Follow-up question node
│   ├── recipe.py           # Recipe generator node (profile-aware)
│   ├── quality.py          # Quality checker node
│   ├── response.py         # Response formatter node
│   └── memory_extractor.py # Regex-based preference extractor (background)
├── api/
│   └── chat.py             # POST /api/chat, GET /api/profile/{session_id}
├── db/
│   └── vector_store.py
├── memory/
│   └── profile.py          # load / save / merge JSON profiles
├── frontend/
│   ├── static/
│   │   └── index.html      # Primary UI (HTML/CSS/JS)
│   └── chat.py             # Legacy Streamlit UI (fallback only)
├── config.py
└── main.py                 # FastAPI app, mounts /static, serves /
data/
├── nutrients/
├── recipes/
├── adh/
├── chroma_db/              # ChromaDB vector store (gitignored)
└── profiles/               # Per-session JSON user profiles (gitignored)
```

## Working Rules

- Make changes as small and local as possible.
- Prefer the existing architecture and file layout in `app/`, `data/`, `scripts/`, and `tests/`.
- When changing behavior, inspect the nearest implementation and the related test first.
- If you change agent flow, retrieval, or response formatting, validate the affected path with `pytest tests/test_agent_graph.py` before expanding scope.
- Memory extraction must never block the response — keep it in a background thread.
- Regex patterns in `memory_extractor.py` are Dutch-language specific. Test changes with the `_extract()` function directly before deploying.
- Update documentation when setup, commands, or user-facing behavior changes.
