from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.api.chat import router as chat_router

app = FastAPI(title="BlendSmart AI", version="0.1.0")
app.include_router(chat_router, prefix="/api")

_STATIC = Path(__file__).parent / "frontend" / "static"
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(_STATIC / "index.html")
