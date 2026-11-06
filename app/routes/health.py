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
    # Sem Redis a API funciona (degradada), então não vira 503. O estado do cache não é
    # exposto nesta rota pública; só vai para o log, para quem opera.
    if not await redis.ping():
        logger.warning("Health check: Redis indisponível (cache e rate limit degradados).")
    return HealthOut(status="ok", banco="ok")
