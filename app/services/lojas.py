from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NaoEncontradoError
from app.models import Loja, Novidade
from app.schemas import LojaCriar, NovidadeCriar


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


async def publicar_novidade(session: AsyncSession, loja_id: int, dados: NovidadeCriar) -> Novidade:
    await obter_loja(session, loja_id)
    novidade = Novidade(loja_id=loja_id, texto=dados.texto, preco=dados.preco)
    session.add(novidade)
    await session.commit()
    return novidade
