"""Perfil do profissional, ciência das responsabilidades e exclusão da conta."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.core.dependencies import SessaoDep, UsuarioDep
from app.schemas.auth import (
    AtualizacaoDePerfil,
    CienciaOut,
    ExclusaoDeConta,
    SessaoOut,
    TokenGoogle,
    TrocaDeSenha,
    UsuarioOut,
)
from app.services import auth as servico
from app.services import imagens as servico_imagens
from app.services.validacao_foto import ler_envio, validar_e_normalizar

router = APIRouter(prefix="/usuarios", tags=["usuário"])


@router.get("/me", response_model=UsuarioOut)
def meu_perfil(usuario: UsuarioDep) -> UsuarioOut:
    return servico.usuario_out(usuario)


@router.patch("/me", response_model=UsuarioOut)
def atualizar_perfil(
    dados: AtualizacaoDePerfil, usuario: UsuarioDep, sessao: SessaoDep
) -> UsuarioOut:
    if dados.nome is not None:
        usuario.nome = dados.nome
    if dados.atuacao is not None:
        usuario.atuacao = dados.atuacao
    sessao.commit()
    sessao.refresh(usuario)
    return servico.usuario_out(usuario)


@router.post("/me/senha", response_model=SessaoOut)
def trocar_senha(dados: TrocaDeSenha, usuario: UsuarioDep, sessao: SessaoDep) -> SessaoOut:
    """Troca a senha e encerra as sessões dos outros aparelhos.

    Devolve tokens novos para este aparelho: os anteriores, inclusive os dele, deixam de
    valer.
    """
    return servico.trocar_senha(sessao, usuario, dados.senha_atual, dados.nova_senha)


@router.delete("/me/sessoes", status_code=status.HTTP_204_NO_CONTENT)
def sair_de_todos_os_aparelhos(usuario: UsuarioDep, sessao: SessaoDep) -> None:
    """Encerra todas as sessões da conta, inclusive a deste aparelho.

    Para quando um aparelho foi perdido ou alguém pode ter copiado o acesso.
    """
    servico.encerrar_todas_as_sessoes(sessao, usuario)


@router.get("/me/ciencia", response_model=CienciaOut)
def minha_ciencia(usuario: UsuarioDep, sessao: SessaoDep) -> CienciaOut:
    return servico.ciencia_atual(sessao, usuario)


@router.post("/me/ciencia", response_model=CienciaOut, status_code=status.HTTP_201_CREATED)
def registrar_ciencia(usuario: UsuarioDep, sessao: SessaoDep) -> CienciaOut:
    return servico.registrar_ciencia(sessao, usuario)


@router.delete("/me/imagens", status_code=status.HTTP_204_NO_CONTENT)
def excluir_imagens(usuario: UsuarioDep, sessao: SessaoDep) -> None:
    """Apaga as imagens e simulações de todos os clientes da conta (LGPD, art. 18).

    Cadastros, histórico de atendimentos, agenda e registros de consentimento permanecem.
    """
    servico_imagens.excluir_todas_as_imagens(sessao, usuario)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def excluir_conta(dados: ExclusaoDeConta, usuario: UsuarioDep, sessao: SessaoDep) -> None:
    """Exclusão física de tudo que pertence à conta (LGPD, art. 18, VI)."""
    servico.excluir_conta(sessao, usuario, dados.senha, dados.id_token_google)


@router.post("/me/google", response_model=UsuarioOut)
def conectar_google(dados: TokenGoogle, usuario: UsuarioDep, sessao: SessaoDep) -> UsuarioOut:
    """Liga uma conta Google à conta de quem está autenticado."""
    return servico.usuario_out(servico.vincular_google(sessao, usuario, dados.id_token, dados.nonce))


@router.delete("/me/google", response_model=UsuarioOut)
def desconectar_google(usuario: UsuarioDep, sessao: SessaoDep) -> UsuarioOut:
    return servico.usuario_out(servico.desvincular_google(sessao, usuario))


@router.post("/me/foto", response_model=UsuarioOut)
def enviar_minha_foto(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    arquivo: Annotated[UploadFile, File(alias="arquivo")],
) -> UsuarioOut:
    """Foto do próprio profissional. Mesma validação técnica das fotos de cliente."""
    foto = validar_e_normalizar(ler_envio(arquivo.file), validar_rosto=False)
    servico_imagens.substituir_foto_do_usuario(sessao, usuario, foto)
    return servico.usuario_out(usuario)


@router.delete("/me/foto", response_model=UsuarioOut)
def remover_minha_foto(usuario: UsuarioDep, sessao: SessaoDep) -> UsuarioOut:
    servico_imagens.remover_foto_do_usuario(sessao, usuario)
    return servico.usuario_out(usuario)
