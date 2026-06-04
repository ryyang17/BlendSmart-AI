# BlendSmart AI — Agentic RAG Chatbot

A local, privacy-first nutrition chatbot powered by **Ollama** + **LangGraph**. BlendSmart AI helps users reach their daily nutritional goals through personalized smoothie and shake recipes — no cloud, no API costs, no internet required.

> **Disclaimer:** BlendSmart AI provides general nutritional information for inspiration only. It is not a medical device and does not offer clinical dietary advice.

---

## What It Does

Users describe their health goals or how they feel (e.g., "Ik voel me altijd moe"), and the agent:

1. **Classifies intent** — recipe request, nutritional info, or needs more context
2. **Asks follow-up questions** if the query is too vague
3. **Retrieves** relevant nutritional data from a local ChromaDB knowledge base
4. **Generates** a concrete smoothie recipe matched to the user's goal and personal profile
5. **Self-evaluates** the answer quality before responding
6. **Remembers** the user's name, allergies, preferences, and favourite ingredients across sessions

This is an **Agentic RAG** system: instead of always running the same retrieve → generate pipeline, the AI agent decides which steps to take based on the situation.

---

## Tech Stack

| Component       | Technology                        | Reason                                      |
|-----------------|-----------------------------------|---------------------------------------------|
| LLM             | Ollama + `qwen2.5:7b`             | Fully local, no API costs, privacy-first    |
| Agent Framework | LangGraph (Python)                | State-machine agentic flows                 |
| Vector Database | ChromaDB                          | Lightweight, local, easy to integrate       |
| Embeddings      | `nomic-embed-text` via Ollama     | Local embeddings, no external API           |
| Backend         | Python + FastAPI                  | REST API + serves the frontend              |
| Frontend        | HTML / CSS / JS (single page)     | Full design control, no extra framework     |
| GPU             | NVIDIA RTX 3050 6 GB              | CUDA support auto-detected by Ollama        |

---

## Architecture

```
Browser (http://localhost:8000)
        │  fetch()
        ▼
  FastAPI Backend
  ├── POST /api/chat
  ├── GET  /api/profile/{session_id}
  └── GET  /  → serves index.html
        │
        ▼
  LangGraph Agent
  ┌──────────────────────────────────────────┐
  │  Intent Classifier                       │
  │       │                                  │
  │  ┌────┴────┐                             │
  │  │         │                             │
  │  ▼         ▼                             │
  │ Follow-up  Retriever (ChromaDB)          │
  │  Node      │                             │
  │            ▼                             │
  │       Recipe Generator ◄── user_profile  │
  │            │                             │
  │            ▼                             │
  │       Quality Checker (retry loop ×2)   │
  │            │                             │
  │            ▼                             │
  │       Response Node                      │
  └──────────────────────────────────────────┘
        │                    │
        ▼                    ▼ (background thread)
  Response to user    Memory Extractor
                      (regex → profile JSON)
        │
        ▼
  Ollama (qwen2.5:7b) — localhost:11434
  ChromaDB — local vector store
  data/profiles/ — persistent user profiles
```

---

## User Memory

BlendSmart AI remembers each user across sessions. Profiles are stored as JSON files in `data/profiles/` (one file per `session_id`, persisted in the browser's `localStorage`).

After each message, a background thread scans the user's text for Dutch phrases and updates the profile — with zero added latency to the response.

**Detected automatically:**

| What the user says | Saved as |
|---|---|
| "Ik heet Ruyi" / "Mijn naam is Sara" | `name` |
| "Ik houd van spinazie en banaan" | `favorite_ingredients` |
| "Ik hou niet van komkommer" | `disliked_ingredients` |
| "Ik ben allergisch voor lactose" | `allergies` |
| "Ik ben veganistisch" | `preferences` |
| "Ik wil meer energie" | `goals` |

The recipe generator automatically adapts its output to the user's known profile.

---

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- NVIDIA GPU with CUDA (RTX 3050 6 GB recommended); CPU fallback is possible but slow

---

## Quick Start

### 1. Clone the repo

```bash
git clone <repo-url>
cd blendsmart-ai
```

### 2. Set up Python environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Pull Ollama models

```bash
ollama pull qwen2.5:7b        # ~4.7 GB — main LLM
ollama pull nomic-embed-text  # embeddings
```

Verify Ollama is running:

```bash
ollama list
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local setup)
```

### 5. Ingest the knowledge base

```bash
python scripts/ingest.py
```

### 6. Run the app

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Project Structure

```
blendsmart-ai/
├── app/
│   ├── agent/
│   │   ├── graph.py            # LangGraph state machine
│   │   ├── state.py            # AgentState (incl. user_profile)
│   │   ├── intent.py           # Intent classifier node
│   │   ├── retriever.py        # ChromaDB retrieval node
│   │   ├── followup.py         # Follow-up question node
│   │   ├── recipe.py           # Recipe generator (profile-aware)
│   │   ├── quality.py          # Quality checker + retry loop
│   │   ├── response.py         # Response formatter
│   │   └── memory_extractor.py # Regex preference extractor (background)
│   ├── api/
│   │   └── chat.py             # POST /api/chat · GET /api/profile/{id}
│   ├── db/
│   │   └── vector_store.py
│   ├── memory/
│   │   └── profile.py          # load / save / merge JSON profiles
│   ├── frontend/
│   │   ├── static/
│   │   │   └── index.html      # Interactive SPA frontend
│   │   └── chat.py             # Legacy Streamlit UI (fallback)
│   ├── config.py
│   └── main.py                 # FastAPI entry point
├── data/
│   ├── nutrients/              # Nutritional data (JSON/Markdown)
│   ├── recipes/                # Smoothie recipes (JSON)
│   ├── adh/                    # RIVM daily intake values
│   ├── chroma_db/              # ChromaDB vector store (gitignored)
│   └── profiles/               # Per-user JSON profiles (gitignored)
├── scripts/
│   └── ingest.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## Frontend Features

The UI is a dark-themed single-page app with these interactive elements:

- **Mood board** — 6 goal cards (⚡ Energie, 🌿 Detox, 💪 Kracht, 🌙 Rust, 🛡️ Immuun, 🎲 Verrassing) that send a preset prompt with one click
- **Quick chips** — shortcut buttons for common requests
- **Recipe cards** — responses containing recipes are rendered in a distinct card format
- **Profile panel** — slide-in panel showing name, favourite ingredients, dislikes, allergies, dietary preferences, and goals as colour-coded tags
- **Personalized greeting** — header updates with the user's name once detected

---

## Example Interaction

```
User:    "Ik voel me altijd moe."

Agent:   "Hoe is je slaap? Eet je regelmatig gedurende de dag?"

User:    "Ik slaap zo'n 6 uur en sla vaak het ontbijt over."

Agent:   Op basis van jouw klachten kan een tekort aan ijzer, magnesium
         en vitamine B12 een rol spelen. Hier is een recept:

         🥤 Spinazie, Banaan & Cacao Power Boost
         - 1 handvol verse spinazie (ijzer, magnesium)
         - 1 rijpe banaan (kalium, B6)
         - 1 el rauwe cacaopoeder (magnesium, antioxidanten)
         - 200 ml havermelk (B12-verrijkt)
         - Optioneel: 1 tl chiazaad

         ⚠️ Dit is algemene voedingsinformatie ter inspiratie, geen medisch advies.
```

---

## Data Sources

- **RIVM Voedingsnormen** — official Dutch daily nutritional intake values (ADH)
- **Voedingscentrum** — ingredient nutritional profiles
- Manually curated smoothie recipes linked to nutritional goals

---

## License

MIT
