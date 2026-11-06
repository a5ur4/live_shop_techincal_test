from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (ou de um arquivo `.env`)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://feed:feed@localhost:5432/feed"
    # Usado só pela suíte de testes; o banco é criado automaticamente se não existir.
    test_database_url: str = "postgresql+asyncpg://feed:feed@localhost:5432/feed_test"
    sql_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
