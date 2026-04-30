from fastapi import APIRouter
from pydantic import BaseModel
from app.agent.graph import agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # TODO: build initial state from request and invoke agent
    raise NotImplementedError
