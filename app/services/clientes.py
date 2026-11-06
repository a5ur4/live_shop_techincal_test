from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflitoError, NaoEncontradoError
from app.core.paginacao import codificar_posicao, decodificar_posicao
from app.core.security import gerar_hash_senha
from app.models import Cliente, Loja, Seguidor
from app.schemas import ClienteCriar, LojaPublica, LojaSeguida, Pagina
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


async def listar_seguindo(
    session: AsyncSession, cliente_id: int, limite: int, cursor: str | None
) -> Pagina[LojaSeguida]:
    """Lojas que o cliente segue, das seguidas mais recentemente para as mais antigas."""
    await obter_cliente(session, cliente_id)
    stmt = (
        select(Seguidor.criado_em, Loja)
        .join(Loja, Loja.id == Seguidor.loja_id)
        .where(Seguidor.cliente_id == cliente_id)
        .order_by(Seguidor.criado_em.desc(), Seguidor.loja_id.desc())
        .limit(limite + 1)
    )
    if cursor:
        stmt = stmt.where(
            tuple_(Seguidor.criado_em, Seguidor.loja_id) < tuple_(*decodificar_posicao(cursor))
        )
    linhas = (await session.execute(stmt)).all()

    tem_mais = len(linhas) > limite
    linhas = linhas[:limite]
    ultimo = linhas[-1] if tem_mais else None
    return Pagina[LojaSeguida](
        itens=[
            LojaSeguida(loja=LojaPublica.model_validate(loja), seguindo_desde=desde)
            for desde, loja in linhas
        ],
        proximo_cursor=codificar_posicao(ultimo[0], ultimo[1].id) if ultimo else None,
    )
