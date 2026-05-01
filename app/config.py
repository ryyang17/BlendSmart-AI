from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen2.5:7b"
    ollama_embed_model: str = "nomic-embed-text-v2-moe"

    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "blendsmart"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    retrieval_top_k: int = 5
    quality_threshold: float = 0.7

    class Config:
        env_file = ".env"


settings = Settings()
