"""Popula o banco com lojas, clientes, relações de seguir e novidades de exemplo.

Uso:
    python -m app.seed            # só popula se o banco estiver vazio
    python -m app.seed --reset    # apaga tudo e popula de novo

No Docker: `docker compose exec api python -m app.seed` (ou `make seed`).

Todas as contas usam a senha SENHA_SEED (apenas para desenvolvimento). E-mail das lojas:
o slug do nome + "@lojas.example.com" (ex.: modadaana@lojas.example.com).
"""

import argparse
import asyncio
import unicodedata
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text

from app.core.db import SessionLocal, engine
from app.core.security import gerar_hash_senha
from app.models import Cliente, Loja, Novidade, Seguidor

SENHA_SEED = "senha123"

LOJAS = ["Moda da Ana", "Tech do Bruno", "Casa & Cia", "Livraria Central", "Esportes Já"]

CLIENTES = [
    ("Carla Souza", "carla@example.com", ["Moda da Ana", "Casa & Cia", "Livraria Central"]),
    ("Diego Lima", "diego@example.com", ["Tech do Bruno", "Esportes Já"]),
    ("Elisa Rocha", "elisa@example.com", LOJAS),
    ("Fábio Nunes", "fabio@example.com", []),
]

NOVIDADES = [
    ("Moda da Ana", "Coleção de verão chegou! Vestidos a partir de R$ 89.", Decimal("89.00")),
    ("Moda da Ana", "Live hoje às 20h com provador ao vivo.", None),
    ("Moda da Ana", "Promoção relâmpago: 30% off em jeans.", Decimal("129.90")),
    ("Tech do Bruno", "Fone bluetooth com cancelamento de ruído.", Decimal("349.00")),
    ("Tech do Bruno", "Aviso: loja fechada no feriado.", None),
    ("Tech do Bruno", "Notebook gamer em pré-venda.", Decimal("6999.99")),
    ("Casa & Cia", "Jogo de panelas antiaderente 5 peças.", Decimal("259.90")),
    ("Casa & Cia", "Frete grátis acima de R$ 200 esta semana.", None),
    ("Livraria Central", "Lançamento: novo romance do autor favorito da casa.", Decimal("59.90")),
    ("Livraria Central", "Clube do livro: encontro sábado às 15h.", None),
    ("Esportes Já", "Tênis de corrida com amortecimento extra.", Decimal("499.00")),
    ("Esportes Já", "Kit academia com 20% de desconto.", Decimal("199.90")),
]


def email_da_loja(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome.lower()).encode("ascii", "ignore").decode()
    slug = "".join(c for c in sem_acento if c.isalnum())
    return f"{slug}@lojas.example.com"


async def seed(reset: bool) -> None:
    async with SessionLocal() as session:
        if reset:
            await session.execute(
                text(
                    "TRUNCATE novidades, seguidores, clientes, lojas, refresh_tokens "
                    "RESTART IDENTITY CASCADE"
                )
            )
        elif await session.scalar(select(func.count()).select_from(Loja)):
            print("Banco já tem dados; nada feito. Use --reset para recriar.")
            return

        senha_hash = gerar_hash_senha(SENHA_SEED)
        lojas = {
            nome: Loja(nome=nome, email=email_da_loja(nome), senha_hash=senha_hash)
            for nome in LOJAS
        }
        session.add_all(lojas.values())
        await session.flush()

        for nome, email, seguidas in CLIENTES:
            cliente = Cliente(nome=nome, email=email, senha_hash=senha_hash)
            session.add(cliente)
            await session.flush()
            session.add_all(Seguidor(cliente_id=cliente.id, loja_id=lojas[n].id) for n in seguidas)

        # Horários espaçados no passado para o feed ter uma ordem interessante.
        agora = datetime.now(UTC)
        for i, (loja, texto_, preco) in enumerate(NOVIDADES):
            session.add(
                Novidade(
                    loja_id=lojas[loja].id,
                    texto=texto_,
                    preco=preco,
                    criado_em=agora - timedelta(hours=len(NOVIDADES) - i),
                )
            )

        await session.commit()

    print(
        f"Seed concluído: {len(LOJAS)} lojas, {len(CLIENTES)} clientes, {len(NOVIDADES)} novidades."
    )
    print(f"Senha de todas as contas: {SENHA_SEED}")
    print("Clientes:", ", ".join(email for _, email, _ in CLIENTES))
    print("Lojas:   ", ", ".join(email_da_loja(n) for n in LOJAS))
    print("Ex.: login de elisa@example.com (segue todas as lojas) e GET /clientes/3/feed.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="apaga os dados antes de popular")
    args = parser.parse_args()
    try:
        await seed(args.reset)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
