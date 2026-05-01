"""Tests for chat session memory."""
from app.api import chat as chat_api


def test_chat_remembers_previous_turns(monkeypatch):
    calls = []

    def fake_invoke(state):
        calls.append([msg.content for msg in state["messages"]])
        return {"final_answer": "ok"}

    monkeypatch.setattr(chat_api.agent, "invoke", fake_invoke)
    chat_api._SESSION_HISTORY.clear()

    first = chat_api.ChatRequest(session_id="session-1", message="Ik voel me moe")
    second = chat_api.ChatRequest(session_id="session-1", message="Ik eet weinig ontbijt")

    first_response = chat_api.chat(first)
    second_response = chat_api.chat(second)

    assert first_response.reply == "ok"
    assert second_response.reply == "ok"
    assert calls[0] == ["Ik voel me moe"]
    assert calls[1] == ["Ik voel me moe", "ok", "Ik eet weinig ontbijt"]