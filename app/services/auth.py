from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NaoAutenticadoError
from app.core.security import TipoConta, Token, criar_token, verificar_senha
from app.models import Cliente, Loja

_MODELOS = {"cliente": Cliente, "loja": Loja}


async def autenticar(session: AsyncSession, tipo: TipoConta, email: str, senha: str) -> Token:
    modelo = _MODELOS[tipo]
    conta = await session.scalar(select(modelo).where(modelo.email == email.strip().lower()))
    # Mesma resposta (e mesmo custo de verificação) para e-mail inexistente e senha errada.
    if not verificar_senha(senha, conta.senha_hash if conta else None):
        raise NaoAutenticadoError("E-mail ou senha incorretos.", codigo="credenciais_invalidas")
    return criar_token(tipo, conta.id)
