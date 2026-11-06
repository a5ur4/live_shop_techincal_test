from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflitoError, NaoEncontradoError
from app.core.security import gerar_hash_senha
from app.models import Loja, Novidade
from app.schemas import LojaCriar, NovidadeCriar


async def obter_loja(session: AsyncSession, loja_id: int) -> Loja:
    loja = await session.get(Loja, loja_id)
    if loja is None:
        raise NaoEncontradoError(f"Loja {loja_id} não encontrada.", codigo="loja_nao_encontrada")
    return loja


async def criar_loja(session: AsyncSession, dados: LojaCriar) -> Loja:
    # Mesmo padrão de clientes: unicidade do e-mail garantida pelo banco (ON CONFLICT).
    stmt = (
        insert(Loja)
        .values(nome=dados.nome, email=dados.email, senha_hash=gerar_hash_senha(dados.senha))
        .on_conflict_do_nothing(index_elements=[Loja.email])
        .returning(Loja)
    )
    loja = await session.scalar(stmt)
    if loja is None:
        raise ConflitoError(
            f"Já existe uma loja com o e-mail {dados.email}.", codigo="email_ja_cadastrado"
        )
    await session.commit()
    return loja


async def publicar_novidade(session: AsyncSession, loja_id: int, dados: NovidadeCriar) -> Novidade:
    await obter_loja(session, loja_id)
    novidade = Novidade(loja_id=loja_id, texto=dados.texto, preco=dados.preco)
    session.add(novidade)
    await session.commit()
    return novidade
