"""Streamlit chat UI for BlendSmart AI — Botanical Luxury theme."""
import streamlit as st
import httpx
from uuid import uuid4

API_URL = "http://localhost:8000/api/chat"

st.set_page_config(
    page_title="BlendSmart AI",
    page_icon="🥤",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Jost:wght@300;400;500&display=swap');

:root {
    --cream:       #f2ede3;
    --parchment:   #e8e1d4;
    --forest:      #1e4d2b;
    --fresh:       #2e7d4f;
    --lime:        #7bc67e;
    --warm-white:  #faf7f2;
    --text-dark:   #1a2b1e;
    --text-mid:    #4a6b52;
    --border:      rgba(30, 77, 43, 0.12);
}

html, body, [class*="css"] {
    font-family: 'Jost', sans-serif !important;
}

.main { background-color: var(--cream) !important; }
.main .block-container {
    max-width: 740px;
    padding-top: 1.5rem;
    padding-bottom: 6rem;
}

#MainMenu, footer, header          { visibility: hidden; }
.stDeployButton                    { display: none; }

/* ── Noise texture ──────────────────────────────────────── */
body::after {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 9999;
}

/* ── Header ─────────────────────────────────────────────── */
.bs-header {
    text-align: center;
    padding: 2.2rem 0 1.6rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
    position: relative;
}
.bs-header::before {
    content: '';
    position: absolute;
    top: 0; left: 50%;
    transform: translateX(-50%);
    width: 48px; height: 3px;
    background: linear-gradient(90deg, var(--lime), var(--fresh));
    border-radius: 2px;
}
.bs-header h1 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 3rem;
    font-weight: 300;
    color: var(--forest);
    letter-spacing: -0.02em;
    margin: 0.4rem 0 0.3rem;
    line-height: 1.1;
}
.bs-header .tagline {
    font-family: 'Jost', sans-serif;
    font-size: 0.72rem;
    font-weight: 400;
    color: var(--text-mid);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-top: 0.4rem;
}
.bs-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(30, 77, 43, 0.07);
    color: var(--fresh);
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 500;
    padding: 0.28rem 0.9rem;
    border-radius: 20px;
    margin-top: 0.9rem;
    border: 1px solid rgba(30, 77, 43, 0.1);
}

/* ── Chat messages ──────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.25rem 0 !important;
    animation: msgIn 0.28s ease forwards;
}
@keyframes msgIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* User bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
  [data-testid="stMarkdownContainer"] {
    background: var(--forest) !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 0.85rem 1.15rem !important;
    max-width: 78%;
    margin-left: auto;
    box-shadow: 0 2px 16px rgba(30, 77, 43, 0.18) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
  [data-testid="stMarkdownContainer"] p {
    color: var(--cream) !important;
    font-size: 0.94rem;
    line-height: 1.55;
    margin: 0;
}

/* Assistant bubble */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])
  [data-testid="stMarkdownContainer"] {
    background: var(--warm-white) !important;
    border-radius: 18px 18px 18px 4px !important;
    padding: 0.85rem 1.15rem !important;
    max-width: 84%;
    border: 1px solid var(--border) !important;
    box-shadow: 0 2px 14px rgba(30, 77, 43, 0.05) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])
  [data-testid="stMarkdownContainer"] p {
    color: var(--text-dark) !important;
    font-size: 0.94rem;
    line-height: 1.6;
    margin: 0;
}

/* Avatars */
[data-testid="chatAvatarIcon-user"]      { background: var(--forest) !important; }
[data-testid="chatAvatarIcon-assistant"] { background: var(--lime)   !important; }

/* ── Chat input ─────────────────────────────────────────── */
[data-testid="stChatInput"] {
    border-radius: 28px !important;
    border: 1.5px solid rgba(30, 77, 43, 0.2) !important;
    background: var(--warm-white) !important;
    box-shadow: 0 4px 24px rgba(30, 77, 43, 0.07) !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--fresh) !important;
    box-shadow: 0 4px 24px rgba(46, 125, 79, 0.14) !important;
}
textarea[data-testid="stChatInputTextArea"] {
    font-family: 'Jost', sans-serif !important;
    font-size: 0.92rem !important;
    color: var(--text-dark) !important;
}

/* ── Spinner ────────────────────────────────────────────── */
.stSpinner > div { border-top-color: var(--fresh) !important; }

/* ── Scrollbar ──────────────────────────────────────────── */
::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(30, 77, 43, 0.18); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(30, 77, 43, 0.35); }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown("""
<div class="bs-header">
    <div style="font-size:2rem">🥤</div>
    <h1>BlendSmart</h1>
    <div class="tagline">Persoonlijke smoothie &amp; voedingsassistent</div>
    <div class="bs-badge">🔒 Volledig lokaal &nbsp;·&nbsp; Geen cloud</div>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid4().hex

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Stel een vraag, bijv. 'Ik voel me altijd moe'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("BlendSmart denkt na..."):
            try:
                resp = httpx.post(
                    API_URL,
                    json={
                        "session_id": st.session_state.session_id,
                        "message": prompt,
                        "history": st.session_state.messages[:-1],
                    },
                    timeout=60,
                )
                reply = resp.json().get("reply", "Er ging iets mis. Probeer opnieuw.")
            except Exception as e:
                reply = f"Kan de backend niet bereiken: {e}"
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
