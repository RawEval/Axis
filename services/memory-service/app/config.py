from __future__ import annotations

from axis_common import AxisBaseSettings


class Settings(AxisBaseSettings):
    service_name: str = "axis-memory-service"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "axis"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "axis-dev-password"
    neo4j_database: str = "neo4j"

    embedding_provider: str = "voyage"
    voyage_api_key: str = ""
    voyage_model: str = "voyage-3"

    memory_episodic_decay_days: int = 90
    memory_max_retrieval_results: int = 20


settings = Settings()
