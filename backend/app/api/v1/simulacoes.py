"""RF04, RF05 e RF07: personalização, geração, consulta e comparação das simulações.

`POST /simulacoes` responde **202** com a simulação em `processando`; o aplicativo
acompanha por `GET /simulacoes/{id}`. A decisão está registrada no diagnóstico (§4.9).

`POST /simulacoes/plano` é a prévia da etapa "Estilo e cor": diz como o pedido será gerado
(modo, modelo e o que vai ao modelo), sem foto e sem custo.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile, status

from app.core.config import obter_config
from app.core.dependencies import SessaoDep, UsuarioDep
from app.core.erros import NaoEncontrado
from app.core.protecoes import conferir_cota_de_simulacoes
from app.repositories import consultas
from app.schemas.simulacao import EnquadramentoOut, PedidoIn, PlanoOut, SimulacaoOut
from app.services import consentimento as servico_consentimento
from app.services import imagens as servico_imagens
from app.services import simulacao as servico
from app.services.ai.pedido import interpretar
from app.services.ai.planos import DESCRICAO_DO_MODO, configuracao_de, planejar
from app.services.validacao_foto import MAX_BYTES_ENQUADRAMENTO, ler_envio, rosto_no_guia

router = APIRouter(prefix="/simulacoes", tags=["simulações"])


@router.post("/plano", response_model=PlanoOut)
def plano(pedido_in: PedidoIn, usuario: UsuarioDep) -> PlanoOut:
    """Prévia, para a tela de revisão: valida o pedido e diz como ele será gerado.

    Usa as regras de escolha sem consultar o provedor (rápido e sem custo). Na geração, o
    schema publicado do modelo é consultado e tem a palavra final.
    """
    pedido = interpretar(
        pedido_in.corte,
        pedido_in.cor,
        manter_corte=pedido_in.manter_corte,
        manter_cor=pedido_in.manter_cor,
        genero=pedido_in.genero,
    )
    config = obter_config()
    escolhido = planejar(pedido, configuracao_de(config))
    return PlanoOut(
        provedor=config.ai_provider,
        modo=escolhido.modo.value,
        descricao_modo=DESCRICAO_DO_MODO[escolhido.modo],
        modelo=escolhido.modelo,
        instrucao=escolhido.instrucao,
        estilo=pedido.rotulo_corte,
        cor=pedido.rotulo_cor,
    )


@router.post("", response_model=SimulacaoOut, status_code=status.HTTP_202_ACCEPTED)
def criar(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    tarefas: BackgroundTasks,
    # Os campos do formulário usam camelCase, como o resto do JSON da API.
    cliente_id: Annotated[uuid.UUID, Form(alias="clienteId")],
    foto: Annotated[UploadFile, File()],
    corte: Annotated[str, Form(max_length=2000)] = "",
    cor: Annotated[str, Form(max_length=2000)] = "",
    manter_corte: Annotated[bool, Form(alias="manterCorte")] = False,
    manter_cor: Annotated[bool, Form(alias="manterCor")] = False,
    # "none", "male" ou "female": o valor do campo `gender` do modelo. Ausente é "none".
    genero: Annotated[str, Form(max_length=20)] = "none",
    chave_envio: Annotated[uuid.UUID | None, Form(alias="chaveEnvio")] = None,
    observacoes: Annotated[str, Form(max_length=2000)] = "",
    demo_recusar_foto: Annotated[bool, Form(alias="demoRecusarFoto")] = False,
    demo_falhar_ia: Annotated[bool, Form(alias="demoFalharIa")] = False,
) -> SimulacaoOut:
    """Recebe a foto e o pedido, e devolve a simulação em processamento.

    O identificador do modelo nunca vem do aplicativo: sai da configuração do servidor,
    conforme o pedido. As duas chaves `demo_*` existem para a demonstração do TCC (foto
    recusada e provedor indisponível) e só têm efeito quando `MODO_DEMO=true`.
    """
    cliente = consultas.cliente_do_usuario(sessao, usuario.id, cliente_id)
    if cliente is None:
        raise NaoEncontrado("Cliente não encontrado.")

    pedido = interpretar(
        corte, cor, manter_corte=manter_corte, manter_cor=manter_cor, genero=genero
    )

    # Antes de ler a foto, validar ou chamar o provedor: com a cota esgotada, nenhum
    # trabalho é feito. A cota só é consumida quando a simulação é criada (no serviço).
    # Um envio repetido não é cobrado de novo: o serviço o devolve antes de tudo.
    if chave_envio is None or servico.ja_enviada(sessao, usuario, chave_envio) is None:
        conferir_cota_de_simulacoes(sessao, usuario.id)

    criada, nova = servico.criar(
        sessao,
        usuario,
        cliente,
        pedido,
        ler_envio(foto.file),
        observacoes=observacoes,
        chave_envio=chave_envio,
        demo_recusar_foto=demo_recusar_foto,
    )
    # Só a simulação recém-criada vai ao provedor. A repetida já tem a tarefa dela.
    if nova:
        tarefas.add_task(
            servico.processar,
            criada.id,
            demo_falhar=demo_falhar_ia and obter_config().modo_demo,
        )
    return servico.como_saida(criada, usuario.id)


@router.post("/enquadramento", response_model=EnquadramentoOut)
def conferir_enquadramento(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    cliente_id: Annotated[uuid.UUID, Form(alias="clienteId")],
    foto: Annotated[UploadFile, File()],
) -> EnquadramentoOut:
    """A tela da câmera pergunta, com uma miniatura, se o rosto está dentro do guia.

    A câmera do Expo não detecta rostos no aparelho; o servidor já tem o detector usado na
    validação da foto. A miniatura não é guardada nem enviada a lugar nenhum, não conta na
    cota de simulações, e só é aceita para cliente com autorização de imagem válida, como
    a própria câmera.
    """
    cliente = consultas.cliente_do_usuario(sessao, usuario.id, cliente_id)
    if cliente is None:
        raise NaoEncontrado("Cliente não encontrado.")
    servico_consentimento.liberar_captura(sessao, cliente)
    return EnquadramentoOut(rosto_no_guia=rosto_no_guia(foto.file.read(MAX_BYTES_ENQUADRAMENTO + 1)))


@router.get("", response_model=list[SimulacaoOut])
def listar(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    cliente_id: Annotated[uuid.UUID | None, Query(alias="clienteId")] = None,
) -> list[SimulacaoOut]:
    servico.expirar_processando(sessao, usuario.id)
    if cliente_id is not None:
        cliente = consultas.cliente_do_usuario(sessao, usuario.id, cliente_id)
        if cliente is None:
            raise NaoEncontrado("Cliente não encontrado.")
        simulacoes = consultas.simulacoes_do_cliente(sessao, cliente.id)
    else:
        simulacoes = consultas.simulacoes_do_usuario(sessao, usuario.id)
    return [servico.como_saida(simulacao, usuario.id) for simulacao in simulacoes]


@router.get("/{simulacao_id}", response_model=SimulacaoOut)
def detalhar(simulacao_id: uuid.UUID, usuario: UsuarioDep, sessao: SessaoDep) -> SimulacaoOut:
    # O aplicativo consulta esta rota enquanto espera: uma geração que morreu com o
    # servidor aparece como falha, em vez de "processando" para sempre.
    servico.expirar_processando(sessao, usuario.id)
    simulacao = consultas.simulacao_do_usuario(sessao, usuario.id, simulacao_id)
    if simulacao is None:
        raise NaoEncontrado("Simulação não encontrada.")
    return servico.como_saida(simulacao, usuario.id)


@router.delete("/{simulacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(simulacao_id: uuid.UUID, usuario: UsuarioDep, sessao: SessaoDep) -> None:
    """Apaga uma simulação e as imagens dela. O histórico de atendimentos permanece.

    A propriedade é conferida aqui: simulação de outra conta responde 404, como se não
    existisse.
    """
    # Uma simulação presa por um reinício precisa poder ser excluída (sem isto, 409).
    servico.expirar_processando(sessao, usuario.id)
    simulacao = consultas.simulacao_do_usuario(sessao, usuario.id, simulacao_id)
    if simulacao is None:
        raise NaoEncontrado("Simulação não encontrada.")
    servico_imagens.excluir_simulacao(sessao, simulacao)


@router.post("/{simulacao_id}/preferida", response_model=SimulacaoOut)
def marcar_preferida(
    simulacao_id: uuid.UUID, usuario: UsuarioDep, sessao: SessaoDep
) -> SimulacaoOut:
    simulacao = servico.marcar_preferida(sessao, usuario, simulacao_id)
    return servico.como_saida(simulacao, usuario.id)
