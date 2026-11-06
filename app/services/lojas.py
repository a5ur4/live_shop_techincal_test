from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NaoEncontradoError
from app.models import Loja
from app.schemas import LojaCriar


async def obter_loja(session: AsyncSession, loja_id: int) -> Loja:
    loja = await session.get(Loja, loja_id)
    if loja is None:
        raise NaoEncontradoError(f"Loja {loja_id} não encontrada.", codigo="loja_nao_encontrada")
    return loja


async def criar_loja(session: AsyncSession, dados: LojaCriar) -> Loja:
    loja = Loja(nome=dados.nome)
    session.add(loja)
    await session.commit()
    return loja
