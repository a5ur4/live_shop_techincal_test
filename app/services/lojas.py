from datetime import UTC, datetime

from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflitoError, NaoEncontradoError
from app.core.paginacao import codificar_id, codificar_posicao, decodificar_id, decodificar_posicao
from app.core.security import gerar_hash_senha
from app.models import Loja, Novidade, Seguidor
from app.schemas import (
    LojaCriar,
    LojaDetalhe,
    LojaPublica,
    NovidadeCriar,
    NovidadeEditar,
    NovidadeOut,
    Pagina,
)


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


def _novidade_nao_encontrada(loja_id: int, novidade_id: int) -> NaoEncontradoError:
    # Novidade de outra loja recebe a mesma resposta de inexistente: não revela que existe.
    return NaoEncontradoError(
        f"Novidade {novidade_id} não encontrada na loja {loja_id}.",
        codigo="novidade_nao_encontrada",
    )


async def editar_novidade(
    session: AsyncSession, loja_id: int, novidade_id: int, dados: NovidadeEditar
) -> Novidade:
    """Edição parcial. `criado_em` não muda (a novidade não "sobe" no feed); marca `editado_em`.

    Como publicar, editar não invalida o cache dos feeds: aparece em até FEED_CACHE_TTL_S.
    """
    novidade = await session.scalar(
        select(Novidade).where(Novidade.id == novidade_id, Novidade.loja_id == loja_id)
    )
    if novidade is None:
        raise _novidade_nao_encontrada(loja_id, novidade_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(novidade, campo, valor)
    novidade.editado_em = datetime.now(UTC)
    await session.commit()
    return novidade


async def remover_novidade(session: AsyncSession, loja_id: int, novidade_id: int) -> None:
    removida = await session.scalar(
        delete(Novidade)
        .where(Novidade.id == novidade_id, Novidade.loja_id == loja_id)
        .returning(Novidade.id)
    )
    if removida is None:
        raise _novidade_nao_encontrada(loja_id, novidade_id)
    await session.commit()


def _escapar_like(termo: str) -> str:
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def listar_lojas(
    session: AsyncSession, limite: int, cursor: str | None, busca: str | None
) -> Pagina[LojaPublica]:
    """Lojas em ordem de cadastro (id crescente), com busca opcional por parte do nome."""
    stmt = select(Loja).order_by(Loja.id).limit(limite + 1)
    if cursor:
        stmt = stmt.where(Loja.id > decodificar_id(cursor))
    if busca:
        stmt = stmt.where(Loja.nome.ilike(f"%{_escapar_like(busca)}%", escape="\\"))
    lojas = list(await session.scalars(stmt))

    tem_mais = len(lojas) > limite
    lojas = lojas[:limite]
    return Pagina[LojaPublica](
        itens=[LojaPublica.model_validate(loja) for loja in lojas],
        proximo_cursor=codificar_id(lojas[-1].id) if tem_mais else None,
    )


async def detalhar_loja(session: AsyncSession, loja_id: int) -> LojaDetalhe:
    loja = await obter_loja(session, loja_id)
    # COUNT pelo índice ix_seguidores_loja_id (index-only scan): ~ms mesmo com 100 mil.
    total = await session.scalar(
        select(func.count()).select_from(Seguidor).where(Seguidor.loja_id == loja_id)
    )
    return LojaDetalhe(
        id=loja.id, nome=loja.nome, criado_em=loja.criado_em, total_seguidores=total or 0
    )


async def listar_novidades(
    session: AsyncSession, loja_id: int, limite: int, cursor: str | None
) -> Pagina[NovidadeOut]:
    """Novidades de uma loja, mais recente primeiro; usa o mesmo índice do feed."""
    await obter_loja(session, loja_id)
    stmt = (
        select(Novidade)
        .where(Novidade.loja_id == loja_id)
        .order_by(Novidade.criado_em.desc(), Novidade.id.desc())
        .limit(limite + 1)
    )
    if cursor:
        stmt = stmt.where(
            tuple_(Novidade.criado_em, Novidade.id) < tuple_(*decodificar_posicao(cursor))
        )
    novidades = list(await session.scalars(stmt))

    tem_mais = len(novidades) > limite
    novidades = novidades[:limite]
    ultimo = novidades[-1] if tem_mais else None
    return Pagina[NovidadeOut](
        itens=[NovidadeOut.model_validate(n) for n in novidades],
        proximo_cursor=codificar_posicao(ultimo.criado_em, ultimo.id) if ultimo else None,
    )
