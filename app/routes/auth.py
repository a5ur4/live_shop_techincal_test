from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.errors import respostas_erro
from app.core.security import TipoConta
from app.routes.deps import RedisDep, SessionDep
from app.schemas import RefreshIn, TokenOut
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["Autenticação"])

FormLogin = Annotated[OAuth2PasswordRequestForm, Depends()]

_DESCRICAO = (
    "OAuth2 *password flow*: envie `username` (o e-mail) e `password` como "
    "`application/x-www-form-urlencoded`. Use o `access_token` no header "
    "`Authorization: Bearer <token>` e o `refresh_token` em `POST /auth/refresh` quando ele "
    "expirar. Após 5 falhas seguidas no mesmo e-mail (ou 20 no mesmo IP) em 15 minutos, "
    "responde 429 com `Retry-After`."
)
_ERROS_LOGIN = respostas_erro("credenciais_invalidas", "muitas_tentativas", "entrada_invalida")


def _ip(request: Request) -> str:
    # Atrás de proxy, rode o uvicorn com --proxy-headers para este IP ser o do cliente.
    return request.client.host if request.client else "desconhecido"


async def _login(tipo: TipoConta, form, request: Request, session, redis) -> TokenOut:
    return await service.autenticar(
        session, redis, tipo, form.username, form.password, _ip(request)
    )


@router.post(
    "/clientes/token",
    response_model=TokenOut,
    responses=_ERROS_LOGIN,
    summary="Login de cliente",
    description=_DESCRICAO,
)
async def token_cliente(form: FormLogin, request: Request, session: SessionDep, redis: RedisDep):
    return await _login("cliente", form, request, session, redis)


@router.post(
    "/lojas/token",
    response_model=TokenOut,
    responses=_ERROS_LOGIN,
    summary="Login de lojista",
    description=_DESCRICAO,
)
async def token_loja(form: FormLogin, request: Request, session: SessionDep, redis: RedisDep):
    return await _login("loja", form, request, session, redis)


@router.post(
    "/refresh",
    response_model=TokenOut,
    responses=respostas_erro("refresh_invalido", "entrada_invalida"),
    summary="Troca o refresh token por um novo par de tokens",
    description=(
        "Rotação: o refresh enviado deixa de valer e um novo é devolvido. Reapresentar um "
        "refresh já usado revoga toda a sessão (sinal de token vazado)."
    ),
)
async def refresh(dados: RefreshIn, session: SessionDep):
    return await service.renovar(session, dados.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=respostas_erro("entrada_invalida"),
    summary="Encerra a sessão do refresh token informado",
    description="Idempotente: responde 204 mesmo para token desconhecido ou já revogado.",
)
async def logout(dados: RefreshIn, session: SessionDep) -> None:
    await service.logout(session, dados.refresh_token)
