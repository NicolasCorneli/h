"""CRUD de clientes (RF02).

A base legal do cadastro é a execução do contrato de serviço (LGPD, art. 7º, V), e não o
consentimento: por isso cliente que recusou a imagem continua com cadastro, histórico e
agenda normais. O consentimento só governa a fotografia.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.erros import NaoEncontrado
from app.models import Cliente, TipoTermo, Usuario
from app.repositories import consultas
from app.schemas.cliente import ClienteAtualizacao, ClienteEntrada, ClienteOut
from app.services import imagens as servico_imagens
from app.services.consentimento import montar_resumo
from app.services.storage import obter_armazenamento, prefixo_do_cliente

log = logging.getLogger(__name__)


def _versao_vigente(sessao: Session) -> str:
    termo = consultas.termo_vigente(sessao, TipoTermo.cliente)
    if termo is None:
        raise NaoEncontrado("Nenhuma versão do termo do cliente está publicada.")
    return termo.versao


#: Marca "não informado" em `como_saida`, distinta de `None` (cliente sem foto).
_BUSCAR = object()


def como_saida(
    sessao: Session,
    usuario: Usuario,
    cliente: Cliente,
    versao_vigente: str | None = None,
    registro=None,
    buscar_registro: bool = True,
    foto=_BUSCAR,
) -> ClienteOut:
    versao = versao_vigente or _versao_vigente(sessao)
    if buscar_registro and registro is None:
        registro = consultas.ultimo_consentimento(sessao, cliente.id)
    if foto is _BUSCAR:
        foto = consultas.foto_do_cliente(sessao, cliente.id)
    return ClienteOut(
        id=cliente.id,
        usuario_id=cliente.usuario_id,
        nome=cliente.nome,
        telefone=cliente.telefone,
        observacoes=cliente.observacoes,
        data_nascimento=cliente.data_nascimento,
        foto_uri=servico_imagens.uri_assinada(foto, usuario.id),
        criado_em=cliente.criado_em,
        consentimento=montar_resumo(cliente, registro, versao),
    )


def listar(sessao: Session, usuario: Usuario, busca: str | None = None) -> list[ClienteOut]:
    versao = _versao_vigente(sessao)
    clientes = consultas.clientes_do_usuario(sessao, usuario.id, busca)
    registros = consultas.ultimos_consentimentos_por_cliente(sessao, usuario.id)
    # Uma consulta para as fotos de todos, em vez de uma por cliente.
    fotos = consultas.fotos_dos_clientes(sessao, usuario.id)
    return [
        como_saida(
            sessao,
            usuario,
            cliente,
            versao_vigente=versao,
            registro=registros.get(cliente.id),
            buscar_registro=False,
            foto=fotos.get(cliente.id),
        )
        for cliente in clientes
    ]


def criar(sessao: Session, usuario: Usuario, dados: ClienteEntrada) -> Cliente:
    cliente = Cliente(
        usuario_id=usuario.id,
        nome=dados.nome,
        telefone=dados.telefone,
        observacoes=dados.observacoes,
        data_nascimento=dados.data_nascimento,
    )
    sessao.add(cliente)
    sessao.commit()
    sessao.refresh(cliente)
    return cliente


def atualizar(sessao: Session, cliente: Cliente, dados: ClienteAtualizacao) -> Cliente:
    if dados.nome is not None:
        cliente.nome = dados.nome
    if dados.telefone is not None:
        cliente.telefone = dados.telefone
    if dados.observacoes is not None:
        cliente.observacoes = dados.observacoes
    if dados.limpar_data_nascimento:
        cliente.data_nascimento = None
    elif dados.data_nascimento is not None:
        cliente.data_nascimento = dados.data_nascimento
    sessao.commit()
    sessao.refresh(cliente)
    return cliente


def excluir(sessao: Session, usuario: Usuario, cliente: Cliente) -> None:
    """Exclusão física, em cascata: consentimentos, simulações, atendimentos e agenda.

    Os objetos de imagem saem do storage antes, porque depois do commit não haveria mais
    como descobrir quais eram.
    """
    servico_imagens.travar_cliente_para_excluir(sessao, cliente_id=cliente.id)
    removidos = obter_armazenamento().excluir_prefixo(prefixo_do_cliente(usuario.id, cliente.id))
    identificador = cliente.id
    sessao.delete(cliente)
    sessao.commit()
    log.info("cliente excluído: id=%s objetos_removidos=%s", identificador, removidos)
