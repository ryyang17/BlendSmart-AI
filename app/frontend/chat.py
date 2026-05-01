"""Streamlit chat UI for BlendSmart AI."""
import streamlit as st
import httpx
from uuid import uuid4

API_URL = "http://localhost:8000/api/chat"

st.set_page_config(page_title="BlendSmart AI", page_icon="🥤")
st.title("🥤 BlendSmart AI")
st.caption("Jouw persoonlijke smoothie- en voedingsassistent — volledig lokaal, geen cloud.")

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
