from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (ou de um arquivo `.env`)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://feed:feed@localhost:5432/feed"
    # Usado só pela suíte de testes; o banco é criado automaticamente se não existir.
    test_database_url: str = "postgresql+asyncpg://feed:feed@localhost:5432/feed_test"
    sql_echo: bool = False
    # Teto de tempo por query no Postgres: protege contra requisições caras (ex.: feed de
    # quem segue milhares de lojas) segurando conexões indefinidamente.
    db_statement_timeout_ms: int = 5000

    # Redis (cache do feed e rate limit). Vazio desliga os dois; a API segue funcionando.
    redis_url: str | None = "redis://localhost:6379/0"
    test_redis_url: str = "redis://localhost:6379/15"
    redis_timeout_s: float = 0.25

    # Autenticação (OAuth2 password flow + JWT). Sem JWT_SECRET definido, uma chave
    # aleatória é gerada a cada start: serve para desenvolvimento, mas invalida os
    # tokens ao reiniciar e não funciona com várias instâncias. Ver docs/adr/0007.
    # HS256 pede chave de pelo menos 32 bytes (RFC 7518, seção 3.2).
    jwt_secret: str | None = Field(default=None, min_length=32)
    jwt_algoritmo: str = "HS256"
    jwt_expira_minutos: int = 30

    @field_validator("jwt_secret", "redis_url", mode="before")
    @classmethod
    def _vazio_e_none(cls, valor: str | None) -> str | None:
        # docker compose passa "" quando a variável não existe no host.
        return valor or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
