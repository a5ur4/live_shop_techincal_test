from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.errors import respostas_erro
from app.routes.deps import SessionDep
from app.schemas import TokenOut
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["Autenticação"])

FormLogin = Annotated[OAuth2PasswordRequestForm, Depends()]

_DESCRICAO = (
    "OAuth2 *password flow*: envie `username` (o e-mail) e `password` como "
    "`application/x-www-form-urlencoded`. Use o `access_token` no header "
    "`Authorization: Bearer <token>`."
)


@router.post(
    "/clientes/token",
    response_model=TokenOut,
    responses=respostas_erro("credenciais_invalidas", "entrada_invalida"),
    summary="Login de cliente (gera access token)",
    description=_DESCRICAO,
)
async def token_cliente(form: FormLogin, session: SessionDep):
    token = await service.autenticar(session, "cliente", form.username, form.password)
    return TokenOut(access_token=token.access_token, expires_in=token.expires_in)


@router.post(
    "/lojas/token",
    response_model=TokenOut,
    responses=respostas_erro("credenciais_invalidas", "entrada_invalida"),
    summary="Login de lojista (gera access token)",
    description=_DESCRICAO,
)
async def token_loja(form: FormLogin, session: SessionDep):
    token = await service.autenticar(session, "loja", form.username, form.password)
    return TokenOut(access_token=token.access_token, expires_in=token.expires_in)
