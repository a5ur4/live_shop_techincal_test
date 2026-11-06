import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import AppError, respostas_erro
from app.routes.deps import RedisDep, SessionDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Saúde"])


class HealthOut(BaseModel):
    status: str
    banco: str
    # Informativo: sem Redis a API funciona (sem cache nem rate limit), então não vira 503.
    cache: str


class BancoIndisponivelError(AppError):
    status_code = 503
    codigo = "banco_indisponivel"


@router.get(
    "/health",
    response_model=HealthOut,
    responses=respostas_erro("banco_indisponivel"),
    summary="Verifica se a API e o banco estão respondendo",
)
async def health(session: SessionDep, redis: RedisDep):
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("Health check falhou: %s", exc)
        raise BancoIndisponivelError("Banco de dados indisponível.") from exc
    cache = "ok" if await redis.ping() else "indisponivel"
    return HealthOut(status="ok", banco="ok", cache=cache)
