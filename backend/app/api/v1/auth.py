"""RF01 — cadastro, login e renovação de sessão."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.dependencies import SessaoDep
from app.schemas.auth import (
    Login,
    ProvedoresOut,
    Registro,
    Renovacao,
    SessaoOut,
    TokenGoogle,
    TokensOut,
)
from app.services import auth as servico
from app.services.google import google_configurado

router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post("/registrar", response_model=SessaoOut, status_code=status.HTTP_201_CREATED)
def registrar(dados: Registro, sessao: SessaoDep) -> SessaoOut:
    return servico.registrar(sessao, dados)


@router.post("/login", response_model=SessaoOut)
def login(dados: Login, sessao: SessaoDep) -> SessaoOut:
    return servico.autenticar(sessao, dados.email, dados.senha)


@router.post("/renovar", response_model=TokensOut)
def renovar(dados: Renovacao, sessao: SessaoDep) -> TokensOut:
    return servico.renovar(sessao, dados.refresh_token)


@router.get("/provedores", response_model=ProvedoresOut)
def provedores() -> ProvedoresOut:
    return ProvedoresOut(google=google_configurado())


@router.post("/google", response_model=SessaoOut)
def entrar_com_google(dados: TokenGoogle, sessao: SessaoDep) -> SessaoOut:
    """Entra com Google; cria a conta no primeiro acesso. Ver `servico.entrar_com_google`."""
    return servico.entrar_com_google(sessao, dados.id_token, dados.nonce)
