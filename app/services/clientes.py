from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflitoError, NaoEncontradoError
from app.core.security import gerar_hash_senha
from app.models import Cliente, Seguidor
from app.schemas import ClienteCriar
from app.services.lojas import obter_loja


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
        .values(nome=dados.nome, email=dados.email, senha_hash=gerar_hash_senha(dados.senha))
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


async def seguir_loja(session: AsyncSession, cliente_id: int, loja_id: int) -> Seguidor:
    await obter_cliente(session, cliente_id)
    await obter_loja(session, loja_id)

    # A PK (cliente_id, loja_id) resolve a corrida entre dois "seguir" iguais.
    stmt = (
        insert(Seguidor)
        .values(cliente_id=cliente_id, loja_id=loja_id)
        .on_conflict_do_nothing(index_elements=[Seguidor.cliente_id, Seguidor.loja_id])
        .returning(Seguidor)
    )
    seguidor = await session.scalar(stmt)
    if seguidor is None:
        raise ConflitoError(
            f"Cliente {cliente_id} já segue a loja {loja_id}.", codigo="ja_segue_loja"
        )
    await session.commit()
    return seguidor


async def deixar_de_seguir(session: AsyncSession, cliente_id: int, loja_id: int) -> None:
    await obter_cliente(session, cliente_id)
    await obter_loja(session, loja_id)

    removido = await session.scalar(
        delete(Seguidor)
        .where(Seguidor.cliente_id == cliente_id, Seguidor.loja_id == loja_id)
        .returning(Seguidor.loja_id)
    )
    if removido is None:
        raise NaoEncontradoError(
            f"Cliente {cliente_id} não segue a loja {loja_id}.", codigo="nao_segue_loja"
        )
    await session.commit()
