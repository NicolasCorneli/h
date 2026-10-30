"""Orquestração da simulação capilar (RF04, RF05, RF07).

A ordem das etapas é a regra, não um detalhe de implementação:

    autenticação → propriedade do cliente → pedido válido → consentimento válido
    → validação da foto → plano conferido no schema do modelo
    → upload da entrada → registro `processando` → (em segundo plano) provedor de IA
    → upload da saída → `concluida`

A chamada ao provedor é a última coisa a acontecer, e só acontece se tudo antes passou.
A simulação nunca nasce `concluida`: ou o resultado foi guardado, ou ela está `falhou`.

O mesmo envio repetido (mesma `chave_envio`) devolve a simulação já criada: um toque
duplo, ou a rede caindo depois de o servidor receber, não paga duas gerações.
"""

from __future__ import annotations

import io
import logging
import uuid
from datetime import UTC, datetime, timedelta

from PIL import Image
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.erros import FotoRecusada, NaoEncontrado, ProvedorIndisponivel, ValidacaoFalhou
from app.core.protecoes import conferir_cota_de_simulacoes
from app.db.session import FabricaSessao
from app.models import Cliente, Simulacao, StatusSimulacao, TipoImagem, Usuario
from app.repositories import consultas
from app.schemas.simulacao import ParametrosSimulacao, SimulacaoOut
from app.services import consentimento as servico_consentimento
from app.services import imagens as servico_imagens
from app.services.ai import EntradaSimulacao, FalhaDoProvedor, SaidaSimulacao, obter_provedor
from app.services.ai.pedido import PedidoCapilar, pedido_registrado
from app.services.ai.planos import Plano
from app.services.storage import obter_armazenamento
from app.services.validacao_foto import FotoValidada, validar_e_normalizar

log = logging.getLogger(__name__)


def como_saida(simulacao: Simulacao, usuario_id: uuid.UUID) -> SimulacaoOut:
    return SimulacaoOut(
        id=simulacao.id,
        cliente_id=simulacao.cliente_id,
        usuario_id=simulacao.usuario_id,
        parametros=ParametrosSimulacao(
            estilo=simulacao.estilo,
            cor=simulacao.cor,
            genero=simulacao.genero,
            observacoes=simulacao.observacoes,
        ),
        status=simulacao.status,
        img_entrada_uri=servico_imagens.uri_assinada(simulacao.img_entrada, usuario_id),
        img_saida_uri=servico_imagens.uri_assinada(simulacao.img_saida, usuario_id),
        modelo_ia=simulacao.modelo_ia,
        provedor=simulacao.provedor,
        instrucao_ia=simulacao.instrucao_ia,
        tempo_ms=simulacao.tempo_ms,
        preferida=simulacao.preferida,
        erro_codigo=simulacao.erro_codigo,
        criado_em=simulacao.criado_em,
        concluida_em=simulacao.concluida_em,
    )


def preparar_no_provedor(pedido: PedidoCapilar) -> tuple[Plano, str]:
    """Escolhe o modelo e confere os parâmetros no schema dele, sem gastar.

    Falha do provedor aqui (credencial recusada, sem crédito, modelo incompatível, fora do
    ar) responde 502 com o motivo, e nada é gravado nem conta na cota.
    """
    try:
        provedor = obter_provedor()
        return provedor.preparar(pedido), provedor.nome
    except FalhaDoProvedor as erro:
        log.warning("o provedor recusou o pedido antes da geração: %s", erro.codigo)
        raise ProvedorIndisponivel(str(erro), codigo=erro.codigo) from erro


def ja_enviada(sessao: Session, usuario: Usuario, chave_envio: uuid.UUID | None) -> Simulacao | None:
    if chave_envio is None:
        return None
    return sessao.scalar(
        select(Simulacao).where(
            Simulacao.usuario_id == usuario.id, Simulacao.chave_envio == chave_envio
        )
    )


def criar(
    sessao: Session,
    usuario: Usuario,
    cliente: Cliente,
    pedido: PedidoCapilar,
    conteudo_foto: bytes,
    *,
    observacoes: str = "",
    chave_envio: uuid.UUID | None = None,
    demo_recusar_foto: bool = False,
) -> tuple[Simulacao, bool]:
    """Cria a simulação em `processando`.

    Devolve a simulação e se ela é nova. Envio repetido devolve a simulação já existente
    com `False`: quem chama não deve processá-la de novo.
    """
    config = obter_config()

    repetida = ja_enviada(sessao, usuario, chave_envio)
    if repetida is not None:
        if repetida.cliente_id != cliente.id:
            raise ValidacaoFalhou(
                "Esta chave de envio já foi usada em outra simulação.", codigo="chave_reutilizada"
            )
        log.info("envio repetido: devolvendo a simulação %s", repetida.id)
        return repetida, False

    # Consentimento antes de tocar na imagem. Levanta 403 com o motivo.
    registro = servico_consentimento.liberar_captura(sessao, cliente)

    if demo_recusar_foto and config.modo_demo:
        raise FotoRecusada(
            "Imagem muito escura",
            detalhes=[
                {
                    "titulo": "Imagem muito escura",
                    "detalhe": "Não dá para separar o cabelo do fundo. Aumente a luz de frente.",
                },
                {
                    "titulo": "Rosto em ângulo",
                    "detalhe": "Vire para frente e reenquadre o rosto dentro do guia.",
                },
            ],
        )

    foto = validar_e_normalizar(conteudo_foto)

    plano, nome_provedor = preparar_no_provedor(pedido)

    # Foto e autorização aprovadas: agora a simulação vai mesmo ao provedor (e custa).
    # Confere a cota de novo, com a conta travada até o commit, para dois envios
    # simultâneos não passarem juntos do teto.
    conferir_cota_de_simulacoes(sessao, usuario.id, travar=True)

    # Com a conta travada, outro envio com a mesma chave pode ter terminado nesse meio
    # tempo: confere de novo antes de gravar.
    repetida = ja_enviada(sessao, usuario, chave_envio)
    if repetida is not None:
        sessao.rollback()
        return repetida, False

    identificador = uuid.uuid4()
    entrada = servico_imagens.registrar(
        sessao, usuario, cliente, TipoImagem.entrada, foto, simulacao_id=identificador
    )

    simulacao = Simulacao(
        id=identificador,
        cliente_id=cliente.id,
        usuario_id=usuario.id,
        consentimento_id=registro.id,
        img_entrada_id=entrada.id,
        estilo=pedido.rotulo_corte,
        cor=pedido.rotulo_cor,
        genero=pedido.genero,
        observacoes=observacoes,
        instrucao_ia=plano.instrucao,
        chave_envio=chave_envio,
        status=StatusSimulacao.processando,
        provedor=nome_provedor,
        modelo_ia=plano.modelo if nome_provedor != "fake" else "provedor local (sem IA)",
    )
    sessao.add(simulacao)
    try:
        sessao.commit()
    except IntegrityError:
        # Duas requisições com a mesma chave chegaram juntas: a outra gravou primeiro.
        sessao.rollback()
        _apagar_objeto(entrada.chave_objeto)
        repetida = ja_enviada(sessao, usuario, chave_envio)
        if repetida is None:  # pragma: no cover - violação de outra restrição
            raise
        return repetida, False
    sessao.refresh(simulacao)
    log.info(
        "simulação criada: id=%s cliente=%s consentimento=%s provedor=%s modo=%s",
        simulacao.id,
        cliente.id,
        registro.id,
        nome_provedor,
        plano.modo,
    )
    return simulacao, True


def processar(simulacao_id: uuid.UUID, *, demo_falhar: bool = False) -> None:
    """Executa a inferência fora do ciclo da requisição (sessão própria).

    Roda em `BackgroundTasks` do FastAPI. A decisão de não usar fila está registrada no
    diagnóstico (§4.9): para o escopo do TCC, uma tarefa em segundo plano mais a consulta
    `GET /simulacoes/{id}` resolvem sem infraestrutura extra.
    """
    with FabricaSessao() as sessao:
        simulacao = sessao.get(Simulacao, simulacao_id)
        if simulacao is None or simulacao.status is not StatusSimulacao.processando:
            return

        pedido = pedido_registrado(simulacao.estilo, simulacao.cor, simulacao.genero)

        usuario = sessao.get(Usuario, simulacao.usuario_id)
        cliente = sessao.get(Cliente, simulacao.cliente_id)
        if usuario is None or cliente is None:
            return

        try:
            if demo_falhar and obter_config().modo_demo:
                raise FalhaDoProvedor(
                    "Falha de provedor simulada para demonstração.", codigo="demonstracao"
                )
            provedor = obter_provedor()
            conteudo_entrada = _bytes_da_entrada(simulacao)
            resultado = provedor.gerar(
                EntradaSimulacao(
                    imagem=conteudo_entrada,
                    mime=simulacao.img_entrada.mime,
                    pedido=pedido,
                )
            )
        except FalhaDoProvedor as erro:
            _marcar_falha(sessao, simulacao, erro.codigo, str(erro))
            return
        except Exception as erro:  # rede, decodificação, storage
            log.exception("erro inesperado ao gerar simulação %s", simulacao.id)
            _marcar_falha(sessao, simulacao, "erro_interno", str(erro))
            return

        # O que o provedor devolveu pode não ser imagem. Isso é problema dele, e o
        # registro precisa dizer isso — não culpar o armazenamento, que nem foi tocado.
        try:
            foto_gerada = _como_foto_validada(resultado)
        except Exception as erro:
            log.error(
                "o provedor devolveu conteúdo que não é imagem: simulacao=%s mime=%s bytes=%s",
                simulacao.id,
                resultado.mime,
                len(resultado.imagem),
            )
            _marcar_falha(sessao, simulacao, "resposta_invalida", str(erro))
            return

        saida = None
        try:
            # A geração pode levar até o tempo limite do provedor. Nesse meio tempo o
            # profissional pode ter apagado as imagens do cliente, o cliente ou a conta.
            # Quem apaga trava o cliente antes de limpar o storage (ver
            # `travar_cliente_para_excluir`); aqui a trava é compartilhada e vem antes de
            # gravar o arquivo. Assim, ou a exclusão termina antes e o resultado é
            # descartado, ou espera este commit e leva o arquivo novo junto.
            cliente_existe = sessao.scalar(
                select(Cliente.id)
                .where(Cliente.id == simulacao.cliente_id)
                .with_for_update(read=True)
            )
            ainda_existe = cliente_existe and sessao.scalar(
                select(Simulacao.id).where(Simulacao.id == simulacao.id)
            )
            if not ainda_existe:
                sessao.rollback()
                log.info("simulação %s apagada durante a geração; resultado descartado", simulacao_id)
                return
            saida = servico_imagens.registrar(
                sessao,
                usuario,
                cliente,
                TipoImagem.saida,
                foto_gerada,
                simulacao_id=simulacao.id,
            )
            simulacao.img_saida_id = saida.id
            simulacao.status = StatusSimulacao.concluida
            # Uma geração muito lenta pode ter sido dada como interrompida no meio do
            # caminho (`expirar_processando`); o resultado que chegou vale, e o erro sai.
            simulacao.erro_codigo = None
            simulacao.erro_detalhe = None
            simulacao.modelo_ia = resultado.modelo
            if resultado.instrucao:
                simulacao.instrucao_ia = resultado.instrucao
            simulacao.tempo_ms = resultado.tempo_ms
            simulacao.concluida_em = datetime.now(UTC)
            sessao.commit()
        except Exception as erro:
            sessao.rollback()
            # O arquivo já foi gravado no storage; sem a linha no banco, ninguém mais o
            # encontraria para apagar. É a foto de uma pessoa: não pode ficar órfã.
            if saida is not None:
                _apagar_objeto(saida.chave_objeto)
            log.exception("falha ao guardar o resultado da simulação %s", simulacao_id)
            try:
                _marcar_falha(sessao, simulacao, "falha_no_armazenamento", str(erro))
            except Exception:  # a simulação pode ter sido apagada no meio do caminho
                sessao.rollback()
                log.warning("não foi possível marcar a falha da simulação %s", simulacao_id)
            return

        log.info(
            "simulação concluída: id=%s modelo=%s tempo_ms=%s",
            simulacao.id,
            resultado.modelo,
            resultado.tempo_ms,
        )


def _apagar_objeto(chave: str) -> None:
    try:
        obter_armazenamento().excluir(chave)
    except Exception:  # pragma: no cover - storage fora do ar
        log.exception("não foi possível apagar o objeto órfão: chave=%s", chave)


def _bytes_da_entrada(simulacao: Simulacao) -> bytes:
    return obter_armazenamento().obter(simulacao.img_entrada.chave_objeto)


def _como_foto_validada(resultado: SaidaSimulacao) -> FotoValidada:
    """A imagem gerada é medida e re-codificada, como qualquer outra que entra no sistema."""
    with Image.open(io.BytesIO(resultado.imagem)) as imagem:
        largura, altura = imagem.size
        convertida = imagem.convert("RGB")
    saida = io.BytesIO()
    convertida.save(saida, format="JPEG", quality=90)
    return FotoValidada(
        conteudo=saida.getvalue(), mime="image/jpeg", largura=largura, altura=altura
    )


def _marcar_falha(sessao: Session, simulacao: Simulacao, codigo: str, detalhe: str) -> None:
    simulacao.status = StatusSimulacao.falhou
    simulacao.erro_codigo = codigo
    simulacao.erro_detalhe = detalhe[:2000]
    simulacao.concluida_em = datetime.now(UTC)
    sessao.commit()
    log.warning("simulação %s falhou: %s", simulacao.id, codigo)


def marcar_preferida(sessao: Session, usuario: Usuario, simulacao_id: uuid.UUID) -> Simulacao:
    """RF07. A propriedade é verificada aqui: não se confia no id vindo do aplicativo."""
    simulacao = consultas.simulacao_do_usuario(sessao, usuario.id, simulacao_id)
    if simulacao is None:
        raise NaoEncontrado("Simulação não encontrada.")
    if simulacao.status is not StatusSimulacao.concluida:
        raise ValidacaoFalhou(
            "Só uma simulação concluída pode ser marcada como preferida.",
            codigo="simulacao_incompleta",
        )

    # Duas marcações simultâneas no mesmo cliente passariam juntas pela troca abaixo e uma
    # delas bateria no índice único (erro 500). A trava no cliente as põe em fila.
    sessao.execute(select(Cliente.id).where(Cliente.id == simulacao.cliente_id).with_for_update())
    # Zera as outras antes de marcar: o índice único parcial admite uma só por cliente.
    for outra in consultas.simulacoes_do_cliente(sessao, simulacao.cliente_id):
        if outra.id != simulacao.id and outra.preferida:
            outra.preferida = False
    sessao.flush()
    simulacao.preferida = True
    sessao.commit()
    sessao.refresh(simulacao)
    return simulacao


def expirar_processando(sessao: Session, usuario_id: uuid.UUID | None = None) -> int:
    """Simulações presas em `processando` (por exemplo, reinício do servidor no meio).

    Nenhuma geração legítima passa de `SIMULACAO_EXPIRA_MIN`: o cliente do provedor
    desiste antes, pelo tempo limite. Passado esse prazo, a tarefa que a gerava morreu.

    Roda na inicialização (todas as contas) e, por conta, antes de listar, mostrar ou
    excluir simulações. Só na inicialização não bastava: uma geração interrompida por um
    reinício tinha menos de 5 minutos naquele momento, escapava da expiração e ficava
    "processando" até o reinício seguinte, sem poder ser excluída (409).
    """
    config = obter_config()
    agora = datetime.now(UTC)
    limite = agora - timedelta(minutes=config.simulacao_expira_min)
    # Um UPDATE só, condicionado ao status: uma geração que conclua neste mesmo instante
    # não é sobrescrita (ler e depois gravar daria `falhou` com imagem de saída, que a
    # restrição do banco recusa com erro 500).
    comando = (
        update(Simulacao)
        .where(Simulacao.status == StatusSimulacao.processando, Simulacao.criado_em < limite)
        .values(
            status=StatusSimulacao.falhou,
            erro_codigo="interrompida",
            erro_detalhe="o processamento foi interrompido antes de concluir",
            concluida_em=agora,
        )
        .execution_options(synchronize_session="fetch")
    )
    if usuario_id is not None:
        comando = comando.where(Simulacao.usuario_id == usuario_id)
    expiradas = sessao.execute(comando).rowcount
    sessao.commit()
    if expiradas:
        log.warning("%s simulações presas em processamento marcadas como falha", expiradas)
    return expiradas
