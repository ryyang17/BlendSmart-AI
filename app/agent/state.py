from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str | None          # "recipe" | "info" | "followup"
    retrieved_docs: list[str]
    needs_followup: bool
    quality_ok: bool
    final_answer: str | None
    retry_count: int
    user_profile: dict          # persistent user preferences
    available_ingredients: list[str]
