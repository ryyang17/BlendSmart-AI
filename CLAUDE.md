# BlendSmart AI Instructions

## Project Context

- BlendSmart AI is a local, privacy-first nutrition chatbot built with FastAPI, LangGraph, Ollama, ChromaDB, and Streamlit.
- Keep the system local by default. Avoid introducing cloud APIs or internet-dependent dependencies unless the user explicitly asks for them.
- The app provides general nutritional information for inspiration only, not medical advice.

## Working Rules

- Make changes as small and local as possible.
- Prefer the existing architecture and file layout in `app/`, `data/`, `scripts/`, and `tests/`.
- When changing behavior, inspect the nearest implementation and the related test first.
- Update documentation when setup, commands, or user-facing behavior changes.

## Python And Validation

- Use the project virtual environment in `.venv` on Windows.
- Prefer running focused tests for the touched area, for example `pytest tests/test_agent_graph.py`.
- If you change agent flow, retrieval, or response formatting, validate the affected path with tests before expanding scope.

## Code Conventions

- Keep prompts, agent nodes, and retrieval logic consistent with the existing RAG flow.
- Preserve the current response style: practical, concise, and nutrition-focused.
- Avoid unnecessary refactors or broad rewrites.

## Useful Entry Points

- API route: `app/api/chat.py`
- Agent graph: `app/agent/graph.py`
- Agent nodes: `app/agent/intent.py`, `app/agent/followup.py`, `app/agent/retriever.py`, `app/agent/recipe.py`, `app/agent/quality.py`, `app/agent/response.py`
- Frontend: `app/frontend/chat.py`
- Ingestion: `scripts/ingest.py`

## Validation Targets

- Use `tests/test_agent_graph.py` for agent flow changes.
- If setup or dependencies change, verify the README instructions still match the project.
