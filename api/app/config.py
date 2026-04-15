"""App configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"

    # Version stamps echoed in every response.
    spec_tag: str = "v0.1.0"
    graph_version: str = "2022-08-23"
    evaluator_version: str = "0.1.0"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
