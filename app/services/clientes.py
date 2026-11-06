from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflitoError, NaoEncontradoError
from app.models import Cliente
from app.schemas import ClienteCriar


async def obter_cliente(session: AsyncSession, cliente_id: int) -> Cliente:
    cliente = await session.get(Cliente, cliente_id)
    if cliente is None:
        raise NaoEncontradoError(
            f"Cliente {cliente_id} não encontrado.", codigo="cliente_nao_encontrado"
        )
    return cliente


async def criar_cliente(session: AsyncSession, dados: ClienteCriar) -> Cliente:
    # ON CONFLICT em vez de "SELECT antes de inserir": a unicidade é garantida
    # pelo banco mesmo com duas requisições simultâneas para o mesmo e-mail.
    stmt = (
        insert(Cliente)
        .values(nome=dados.nome, email=dados.email)
        .on_conflict_do_nothing(index_elements=[Cliente.email])
        .returning(Cliente)
    )
    cliente = await session.scalar(stmt)
    if cliente is None:
        raise ConflitoError(
            f"Já existe um cliente com o e-mail {dados.email}.", codigo="email_ja_cadastrado"
        )
    await session.commit()
    return cliente
