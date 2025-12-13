from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_url: str = "bolt://neo4j:test1234@localhost:7687"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_prefer_grpc: bool = False

    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    openai_api_key: str = ""
    openai_base_url: Optional[str] = ""
    openai_model: str = "gpt-4o-mini"
    openai_cheap_model: str = "gpt-4o-mini"

    max_recursion_depth: int = 3
    search_top_k: int = 5

    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "OBSIDIAN_RAG_", "env_file": ".env"}


settings = Settings()
