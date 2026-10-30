"""Recebimento, entrega e exclusão de imagens.

Imagem de pessoa é dado sensível: aqui ela nunca ganha URL pública permanente, nunca é
gravada com nome vindo do cliente e nunca sai do servidor sem assinatura válida.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.contexto import base_url
from app.core.erros import ArmazenamentoIndisponivel, Conflito, NaoEncontrado
from app.core.security import assinar_imagem, verificar_assinatura_imagem
from app.models import Cliente, Imagem, Simulacao, StatusSimulacao, TipoImagem, Usuario
from app.repositories import consultas
from app.services.storage import (
    ObjetoNaoEncontrado,
    montar_chave,
    obter_armazenamento,
    prefixo_do_cliente,
)
from app.services.validacao_foto import FotoValidada

log = logging.getLogger(__name__)


def travar_cliente_para_excluir(sessao: Session, *, cliente_id=None, usuario_id=None) -> None:
    """Trava o(s) cliente(s) antes de apagar arquivos do storage.

    Uma simulação em andamento grava o resultado depois de travar o cliente em modo
    compartilhado. Com esta trava exclusiva antes de limpar o storage, a exclusão espera a
    gravação em curso terminar (e então apaga o arquivo novo junto), ou a gravação espera
    a exclusão e descarta o resultado. Sem ela, o arquivo gerado no meio da exclusão ficava
    no disco sem registro que o encontrasse: a foto de uma pessoa, órfã, depois de ela
    pedir a eliminação.
    """
    consulta = select(Cliente.id).with_for_update()
    if cliente_id is not None:
        consulta = consulta.where(Cliente.id == cliente_id)
    else:
        consulta = consulta.where(Cliente.usuario_id == usuario_id).order_by(Cliente.id)
    sessao.execute(consulta)


def uri_assinada(imagem: Imagem | None, usuario_id: uuid.UUID) -> str | None:
    if imagem is None:
        return None
    token = assinar_imagem(imagem.id, usuario_id)
    # `URL_PUBLICA` quando configurada (produção, atrás de proxy); senão, o endereço da
    # própria requisição (desenvolvimento, celular na rede local).
    raiz = obter_config().url_publica or base_url()
    return f"{raiz}/api/v1/imagens/{imagem.id}?t={token}"


def registrar(
    sessao: Session,
    usuario: Usuario,
    cliente: Cliente | None,
    tipo: TipoImagem,
    foto: FotoValidada,
    simulacao_id: uuid.UUID | None = None,
) -> Imagem:
    """Grava o objeto no storage e a linha de metadados.

    Se o banco falhar depois do upload, o objeto é removido no `except` para não deixar
    arquivo órfão (seção 30 da especificação).
    """
    chave = montar_chave(
        usuario.id, cliente.id if cliente else None, tipo, foto.mime, simulacao_id
    )
    armazenamento = obter_armazenamento()
    try:
        armazenamento.salvar(chave, foto.conteudo, foto.mime)
    except OSError as erro:
        log.exception("falha ao gravar objeto no storage: chave=%s", chave)
        raise ArmazenamentoIndisponivel("Não foi possível guardar a imagem agora.") from erro

    imagem = Imagem(
        usuario_id=usuario.id,
        cliente_id=cliente.id if cliente else None,
        tipo=tipo,
        chave_objeto=chave,
        mime=foto.mime,
        bytes=len(foto.conteudo),
        largura=foto.largura,
        altura=foto.altura,
    )
    try:
        sessao.add(imagem)
        sessao.flush()
    except Exception:
        sessao.rollback()
        armazenamento.excluir(chave)
        raise
    return imagem


def substituir_foto_de_perfil(
    sessao: Session, usuario: Usuario, cliente: Cliente, foto: FotoValidada
) -> Imagem:
    """Só existe uma foto de perfil por cliente (índice único parcial em `imagens`)."""
    anterior = next(
        (
            imagem
            for imagem in consultas.imagens_do_cliente(sessao, cliente.id)
            if imagem.tipo is TipoImagem.perfil
        ),
        None,
    )
    if anterior is not None:
        obter_armazenamento().excluir(anterior.chave_objeto)
        sessao.delete(anterior)
        sessao.flush()

    imagem = registrar(sessao, usuario, cliente, TipoImagem.perfil, foto)
    sessao.commit()
    sessao.refresh(imagem)
    return imagem


def substituir_foto_do_usuario(sessao: Session, usuario: Usuario, foto: FotoValidada) -> Imagem:
    """Foto do próprio profissional (Meus dados). Uma só: a anterior sai do storage."""
    anterior = consultas.foto_do_usuario(sessao, usuario.id)
    if anterior is not None:
        obter_armazenamento().excluir(anterior.chave_objeto)
        sessao.delete(anterior)
        sessao.flush()
    imagem = registrar(sessao, usuario, None, TipoImagem.perfil, foto)
    sessao.commit()
    sessao.refresh(imagem)
    return imagem


def remover_foto_do_usuario(sessao: Session, usuario: Usuario) -> None:
    anterior = consultas.foto_do_usuario(sessao, usuario.id)
    if anterior is not None:
        obter_armazenamento().excluir(anterior.chave_objeto)
        sessao.delete(anterior)
    sessao.commit()


def remover_foto_de_perfil(sessao: Session, cliente: Cliente) -> None:
    for imagem in consultas.imagens_do_cliente(sessao, cliente.id):
        if imagem.tipo is TipoImagem.perfil:
            obter_armazenamento().excluir(imagem.chave_objeto)
            sessao.delete(imagem)
    sessao.commit()


def excluir_simulacoes_do_cliente(sessao: Session, usuario: Usuario, cliente: Cliente) -> int:
    """`DELETE /clientes/{id}/simulacoes` — art. 18 da LGPD.

    Apaga as simulações e **todos** os objetos de imagem do cliente, inclusive a foto de
    perfil. O histórico de atendimentos continua existindo: o vínculo com a simulação cai
    para `NULL` pela própria chave estrangeira, e não por código.
    O histórico de consentimentos também é preservado — é o registro da decisão, não a imagem.
    """
    # A trava vem antes de listar: o que for gravado por uma simulação em andamento
    # entra na lista, em vez de escapar dela.
    travar_cliente_para_excluir(sessao, cliente_id=cliente.id)
    simulacoes = consultas.simulacoes_do_cliente(sessao, cliente.id)
    imagens = consultas.imagens_do_cliente(sessao, cliente.id)

    removidos = obter_armazenamento().excluir_prefixo(prefixo_do_cliente(usuario.id, cliente.id))
    for simulacao in simulacoes:
        sessao.delete(simulacao)
    sessao.flush()
    for imagem in imagens:
        sessao.delete(imagem)
    sessao.commit()

    log.info(
        "imagens excluídas: cliente=%s simulacoes=%s imagens=%s objetos=%s",
        cliente.id,
        len(simulacoes),
        len(imagens),
        removidos,
    )
    return len(simulacoes)


def excluir_simulacao(sessao: Session, simulacao: Simulacao) -> None:
    """`DELETE /simulacoes/{id}`: apaga uma simulação e as duas imagens dela.

    Saem a foto enviada e a imagem gerada, do banco e do storage. O histórico de
    atendimentos continua: o vínculo com a simulação cai para `NULL` pela própria chave
    estrangeira, como na exclusão de todas as simulações do cliente.

    Uma simulação ainda em processamento não é apagada: a geração em segundo plano ainda
    vai gravar nela, e o profissional pode excluí-la assim que ela concluir ou falhar.
    """
    # A mesma trava da exclusão por cliente: uma gravação de resultado em curso termina
    # antes, e o estado lido depois dela é o que vale.
    travar_cliente_para_excluir(sessao, cliente_id=simulacao.cliente_id)
    sessao.refresh(simulacao)
    if simulacao.status is StatusSimulacao.processando:
        sessao.rollback()
        raise Conflito(
            "Esta simulação ainda está sendo gerada. Aguarde concluir para excluir.",
            codigo="simulacao_em_processamento",
        )

    imagens = [imagem for imagem in (simulacao.img_entrada, simulacao.img_saida) if imagem is not None]
    armazenamento = obter_armazenamento()
    for imagem in imagens:
        armazenamento.excluir(imagem.chave_objeto)
    identificador, cliente_id = simulacao.id, simulacao.cliente_id
    sessao.delete(simulacao)
    sessao.flush()
    for imagem in imagens:
        sessao.delete(imagem)
    sessao.commit()
    log.info(
        "simulação excluída: id=%s cliente=%s imagens=%s", identificador, cliente_id, len(imagens)
    )


def excluir_todas_as_imagens(sessao: Session, usuario: Usuario) -> int:
    """Exclusão de todas as imagens da conta, de uma vez (tela de privacidade).

    Equivale a chamar a exclusão por cliente em cada um deles, e existe para que o
    aplicativo não precise de uma requisição por cliente. Histórico de atendimentos e de
    consentimentos continuam intactos.
    """
    total = 0
    for cliente in consultas.clientes_do_usuario(sessao, usuario.id):
        total += excluir_simulacoes_do_cliente(sessao, usuario, cliente)
    return total


def entregar(
    sessao: Session, imagem_id: uuid.UUID, token: str
) -> tuple[bytes | None, str, str | None]:
    """Devolve `(conteudo, mime, url_externa)`.

    Aqui **a assinatura é a autorização**, e não o cabeçalho Bearer: o `<Image>` do React
    Native não envia cabeçalhos. A conferência usa o dono registrado da própria imagem, de
    modo que só uma assinatura emitida por este servidor, para esta imagem e este dono,
    dentro da validade, abre o arquivo.

    Com driver S3 há URL pré-assinada e o endpoint apenas redireciona; com driver local os
    bytes saem pela própria API.
    """
    imagem = sessao.get(Imagem, imagem_id)
    if imagem is None:
        raise NaoEncontrado("Imagem não encontrada.")
    if not verificar_assinatura_imagem(token, imagem.id, imagem.usuario_id):
        raise NaoEncontrado("Imagem não encontrada.")

    armazenamento = obter_armazenamento()
    externa = armazenamento.url_temporaria(imagem.chave_objeto)
    if externa:
        return None, imagem.mime, externa
    try:
        return armazenamento.obter(imagem.chave_objeto), imagem.mime, None
    except ObjetoNaoEncontrado as erro:
        log.error("objeto ausente no storage: chave=%s", imagem.chave_objeto)
        raise NaoEncontrado("Imagem não encontrada.") from erro
