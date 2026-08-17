from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Single source of truth for configuration.

    Why a class instead of just os.environ.get() scattered everywhere:
    - One place to see every config value the app depends on
    - Pydantic validates types at startup (e.g. catches a malformed URL
      immediately, instead of failing confusingly deep in a DB call later)
    - Easy to override in tests: Settings(postgres_url="sqlite://...")
    """

    postgres_url: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    github_token: str
    openai_api_key: str

    class Config:
        # Reads a .env file if present (useful for local dev without Docker);
        # in Docker, the values come from docker-compose.yml's `environment:`
        # block instead, which takes precedence.
        env_file = ".env"


# Instantiated once at import time. FastAPI code elsewhere does
# `from app.core.config import settings` and uses it directly —
# no need to re-read env vars in multiple places.
settings = Settings()
