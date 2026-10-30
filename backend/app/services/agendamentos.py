"""Agenda (RF06): criação, edição, confirmação, cancelamento e conclusão.

Regras que o servidor impõe, independentemente da tela:

1. **Nada no passado.** Um compromisso não pode ser marcado, nem remarcado, para um
   instante que já passou. A comparação é entre instantes com fuso, o que a torna imune à
   confusão entre UTC e o horário local: 23h de Brasília e 02h UTC do dia seguinte são o
   mesmo instante. Há uma tolerância curta para diferença de relógio entre aparelho e
   servidor.
2. **Sem sobreposição.** Dois compromissos ativos do mesmo profissional não ocupam o mesmo
   horário. Cancelados e concluídos não contam.
3. **Estados finais são finais.** Cancelado e concluído não voltam atrás nem são editados.
4. **Concluir gera o atendimento.** Na mesma transação: o agendamento muda de status e o
   atendimento nasce vinculado a ele. Ou os dois acontecem, ou nenhum. Repetir a conclusão
   devolve o atendimento já criado, sem duplicar; o índice único no banco garante o mesmo
   mesmo que duas requisições cheguem juntas.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.erros import NaoEncontrado, ValidacaoFalhou
from app.models import Agendamento, Atendimento, StatusAgendamento, Usuario
from app.models.enums import TRANSICOES_AGENDAMENTO
from app.repositories import consultas
from app.schemas.agendamento import AgendamentoAtualizacao, AgendamentoEntrada, Conclusao

#: Folga para relógios levemente diferentes entre o aparelho e o servidor.
TOLERANCIA = timedelta(minutes=5)

ROTULOS = {
    StatusAgendamento.pendente: "aguardando confirmação",
    StatusAgendamento.confirmado: "confirmado",
    StatusAgendamento.cancelado: "cancelado",
    StatusAgendamento.concluido: "concluído",
}

FINAIS = {StatusAgendamento.cancelado, StatusAgendamento.concluido}


def _agora() -> datetime:
    return datetime.now(UTC)


def _validar_nao_passado(data_hora: datetime) -> None:
    if data_hora < _agora() - TOLERANCIA:
        raise ValidacaoFalhou(
            "Esse horário já passou. Escolha uma data e um horário a partir de agora.",
            codigo="data_passada",
            detalhes=[{"campo": "dataHora"}],
        )


def dia_do_atendimento(realizado_em: datetime, mensagem: str, codigo: str):
    """Confere que o atendimento não está no futuro e devolve o dia, no fuso do salão.

    Regra única para os dois jeitos de registrar um atendimento: concluindo um agendamento
    ou direto pelo perfil do cliente.
    """
    if realizado_em > _agora() + TOLERANCIA:
        raise ValidacaoFalhou(mensagem, codigo=codigo, detalhes=[{"campo": "realizadoEm"}])
    return realizado_em.astimezone(obter_config().fuso).date()


def hoje_no_salao():
    """A data de hoje no fuso do salão (não no do servidor, que costuma estar em UTC)."""
    return _agora().astimezone(obter_config().fuso).date()


def validar_dia_nao_futuro(dia, mensagem: str, codigo: str) -> None:
    """Um atendimento registrado só pelo dia não pode estar depois de hoje.

    "Hoje" é o maior entre o dia no fuso do salão e o dia em UTC. O aparelho manda a data
    do calendário dele, e o Brasil inteiro está atrás de UTC: às 22h de Brasília um
    aparelho em Fernando de Noronha (ou com relógio em UTC) já está no dia seguinte. A
    folga cobre isso e ainda recusa o que é de fato futuro (semana que vem, 2099).
    """
    limite = max(hoje_no_salao(), _agora().date())
    if dia > limite:
        raise ValidacaoFalhou(mensagem, codigo=codigo, detalhes=[{"campo": "dataServico"}])


def _validar_sem_conflito(
    sessao: Session,
    usuario_id: uuid.UUID,
    inicio: datetime,
    duracao_min: int | None,
    ignorar_id: uuid.UUID | None = None,
) -> None:
    """Recusa sobreposição com outro compromisso ativo do mesmo profissional.

    Sem duração informada, o compromisso ocupa só o horário de início: conflita com quem
    começa no mesmo horário ou com um compromisso em andamento naquele instante. Não se
    presume duração nenhuma para preencher a lacuna.
    """
    fim = inicio + timedelta(minutes=duracao_min or 0)
    termino_existente = Agendamento.data_hora + func.make_interval(
        0, 0, 0, 0, 0, func.coalesce(Agendamento.duracao_min, 0)
    )
    consulta = select(Agendamento).where(
        Agendamento.usuario_id == usuario_id,
        Agendamento.status.in_([StatusAgendamento.pendente, StatusAgendamento.confirmado]),
        or_(
            and_(Agendamento.data_hora < fim, termino_existente > inicio),
            Agendamento.data_hora == inicio,
        ),
    )
    if ignorar_id is not None:
        consulta = consulta.where(Agendamento.id != ignorar_id)
    choque = sessao.scalars(consulta.order_by(Agendamento.data_hora).limit(1)).first()
    if choque is not None:
        fuso = obter_config().fuso
        horario = choque.data_hora.astimezone(fuso).strftime("%d/%m às %H:%M")
        raise ValidacaoFalhou(
            f"Esse horário coincide com outro agendamento ({horario}, {choque.servico}). "
            "Escolha outro horário ou altere o agendamento existente.",
            codigo="horario_ocupado",
            detalhes=[{"campo": "dataHora", "conflitoCom": str(choque.id)}],
        )


def _travar_agenda(sessao: Session, usuario_id: uuid.UUID) -> None:
    """Serializa as gravações na agenda de um profissional até o fim da transação.

    A conferência de conflito é uma leitura seguida de uma escrita. Sem trava, dois envios
    simultâneos (um toque duplo, dois aparelhos) leem a agenda vazia ao mesmo tempo e os
    dois gravam o mesmo horário. Travar a linha da conta faz o segundo esperar o primeiro
    terminar e então enxergar o horário já ocupado. A trava é por profissional: agendas de
    contas diferentes não esperam umas pelas outras.
    """
    sessao.execute(select(Usuario.id).where(Usuario.id == usuario_id).with_for_update())


def _reler_com_trava(sessao: Session, agendamento: Agendamento) -> Agendamento:
    """Trava a linha do agendamento e relê o estado atual dela.

    Toda mudança de status decide a partir do status atual: confirmar, cancelar, editar e
    concluir. Sem a trava, duas requisições simultâneas (dois aparelhos, um toque duplo)
    decidem sobre o mesmo status antigo e a segunda desfaz a primeira, por exemplo
    confirmando um compromisso que acabou de ser cancelado.

    `populate_existing` é indispensável: o agendamento já foi lido nesta sessão antes da
    trava, e sem ele a sessão devolveria o objeto que tem em memória, com o status de
    antes de a outra requisição terminar.
    """
    return sessao.scalars(
        select(Agendamento)
        .where(Agendamento.id == agendamento.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def _cliente(sessao: Session, usuario: Usuario, cliente_id: uuid.UUID):
    cliente = consultas.cliente_do_usuario(sessao, usuario.id, cliente_id)
    if cliente is None:
        raise NaoEncontrado("Cliente não encontrado.")
    return cliente


def _exigir_editavel(agendamento: Agendamento) -> None:
    if agendamento.status in FINAIS:
        raise ValidacaoFalhou(
            f"Este agendamento já foi {ROTULOS[agendamento.status]} e não pode mais ser alterado.",
            codigo="agendamento_finalizado",
        )


def _exigir_transicao(agendamento: Agendamento, novo: StatusAgendamento) -> None:
    permitidos = TRANSICOES_AGENDAMENTO[agendamento.status]
    if novo not in permitidos:
        raise ValidacaoFalhou(
            f"Não é possível mudar de {ROTULOS[agendamento.status]} para {ROTULOS[novo]}.",
            codigo="transicao_invalida",
            detalhes=[{"de": agendamento.status.value, "permitidos": [s.value for s in permitidos]}],
        )


# --- Criação e edição -------------------------------------------------------


def criar(sessao: Session, usuario: Usuario, dados: AgendamentoEntrada) -> Agendamento:
    cliente = _cliente(sessao, usuario, dados.cliente_id)
    _validar_nao_passado(dados.data_hora)
    _travar_agenda(sessao, usuario.id)
    _validar_sem_conflito(sessao, usuario.id, dados.data_hora, dados.duracao_min)

    agendamento = Agendamento(
        cliente_id=cliente.id,
        usuario_id=usuario.id,
        data_hora=dados.data_hora,
        servico=dados.servico,
        duracao_min=dados.duracao_min,
        observacoes=dados.observacoes,
        lembrete=dados.lembrete,
        status=StatusAgendamento.pendente,
    )
    sessao.add(agendamento)
    sessao.commit()
    sessao.refresh(agendamento)
    return agendamento


def atualizar(
    sessao: Session, usuario: Usuario, agendamento: Agendamento, dados: AgendamentoAtualizacao
) -> Agendamento:
    agendamento = _reler_com_trava(sessao, agendamento)
    _exigir_editavel(agendamento)

    if dados.cliente_id is not None and dados.cliente_id != agendamento.cliente_id:
        agendamento.cliente_id = _cliente(sessao, usuario, dados.cliente_id).id

    nova_data = dados.data_hora if dados.data_hora is not None else agendamento.data_hora
    # `duracaoMin` ausente mantém a atual; enviada como null, apaga (campo opcional).
    nova_duracao = (
        dados.duracao_min if "duracao_min" in dados.model_fields_set else agendamento.duracao_min
    )

    # A data só é conferida quando muda: editar a observação de um compromisso de hoje
    # cedo, já passado, não pode ser recusado por causa do horário que ninguém alterou.
    if dados.data_hora is not None and dados.data_hora != agendamento.data_hora:
        _validar_nao_passado(dados.data_hora)
    if nova_data != agendamento.data_hora or nova_duracao != agendamento.duracao_min:
        _travar_agenda(sessao, usuario.id)
        _validar_sem_conflito(sessao, usuario.id, nova_data, nova_duracao, agendamento.id)

    agendamento.data_hora = nova_data
    agendamento.duracao_min = nova_duracao
    if dados.servico is not None:
        agendamento.servico = dados.servico
    if dados.observacoes is not None:
        agendamento.observacoes = dados.observacoes
    if dados.lembrete is not None:
        agendamento.lembrete = dados.lembrete
    sessao.commit()
    sessao.refresh(agendamento)
    return agendamento


# --- Mudanças de status -----------------------------------------------------


def confirmar(sessao: Session, agendamento: Agendamento) -> Agendamento:
    agendamento = _reler_com_trava(sessao, agendamento)
    if agendamento.status is StatusAgendamento.confirmado:
        return agendamento
    _exigir_transicao(agendamento, StatusAgendamento.confirmado)
    agendamento.status = StatusAgendamento.confirmado
    sessao.commit()
    sessao.refresh(agendamento)
    return agendamento


def cancelar(sessao: Session, agendamento: Agendamento, motivo: str = "") -> Agendamento:
    """Cancela preservando o registro: o compromisso sai da agenda ativa, não do banco."""
    agendamento = _reler_com_trava(sessao, agendamento)
    if agendamento.status is StatusAgendamento.cancelado:
        return agendamento
    _exigir_transicao(agendamento, StatusAgendamento.cancelado)
    agendamento.status = StatusAgendamento.cancelado
    agendamento.cancelado_em = _agora()
    agendamento.motivo_cancelamento = motivo.strip()
    sessao.commit()
    sessao.refresh(agendamento)
    return agendamento


def concluir(
    sessao: Session, usuario: Usuario, agendamento: Agendamento, dados: Conclusao
) -> Atendimento:
    """Conclui o compromisso e cria o atendimento, numa única transação.

    Idempotente: concluir de novo devolve o atendimento existente. A linha do agendamento
    é travada durante a operação, para que duas requisições simultâneas não criem dois
    atendimentos; o índice único em `atendimentos.agendamento_id` é a segunda barreira.
    """
    travado = _reler_com_trava(sessao, agendamento)

    if travado.status is StatusAgendamento.concluido:
        existente = sessao.scalars(
            select(Atendimento).where(Atendimento.agendamento_id == travado.id)
        ).first()
        if existente is not None:
            sessao.commit()
            return existente
        # Concluído antes de esta relação existir: o atendimento nunca foi gerado. Não se
        # inventa um agora; o histórico daquele dia é o que foi registrado à época.
        sessao.rollback()
        raise ValidacaoFalhou(
            "Este agendamento foi concluído antes de o sistema registrar o atendimento "
            "junto. Registre o serviço pelo histórico do cliente, se precisar.",
            codigo="concluido_sem_atendimento",
        )

    _exigir_transicao(travado, StatusAgendamento.concluido)

    realizado_em = dados.realizado_em or _agora()
    try:
        dia = dia_do_atendimento(
            realizado_em, "O horário de conclusão não pode estar no futuro.", "conclusao_no_futuro"
        )
    except ValidacaoFalhou:
        sessao.rollback()
        raise

    if dados.simulacao_id is not None:
        simulacao = consultas.simulacao_do_usuario(sessao, usuario.id, dados.simulacao_id)
        if simulacao is None:
            sessao.rollback()
            raise NaoEncontrado("Simulação não encontrada.")
        if simulacao.cliente_id != travado.cliente_id:
            sessao.rollback()
            raise ValidacaoFalhou(
                "Essa simulação é de outro cliente.", codigo="simulacao_de_outro_cliente"
            )

    atendimento = Atendimento(
        cliente_id=travado.cliente_id,
        usuario_id=usuario.id,
        agendamento_id=travado.id,
        simulacao_id=dados.simulacao_id,
        descricao=(dados.descricao or travado.servico).strip(),
        # O dia em que o serviço aconteceu, no fuso do salão. Não é o dia marcado: quem
        # conclui hoje um atendimento de ontem registra o dia em que ele de fato ocorreu.
        data_servico=dia,
        realizado_em=realizado_em,
        duracao_min=dados.duracao_min,
        observacoes=(dados.observacoes if dados.observacoes is not None else travado.observacoes),
    )
    travado.status = StatusAgendamento.concluido
    sessao.add(atendimento)
    sessao.commit()
    sessao.refresh(atendimento)
    return atendimento


def mudar_status(
    sessao: Session, usuario: Usuario, agendamento: Agendamento, novo: StatusAgendamento
) -> Agendamento:
    """Rota genérica de status, mantida por compatibilidade.

    Cancelar e concluir passam pelas mesmas funções das rotas próprias. Sem isso, a rota
    genérica seria uma porta lateral para concluir sem gerar atendimento.
    """
    if novo is StatusAgendamento.confirmado:
        return confirmar(sessao, agendamento)
    if novo is StatusAgendamento.cancelado:
        return cancelar(sessao, agendamento)
    if novo is StatusAgendamento.concluido:
        concluir(sessao, usuario, agendamento, Conclusao())
        sessao.refresh(agendamento)
        return agendamento
    _exigir_transicao(agendamento, novo)
    return agendamento


def excluir(sessao: Session, agendamento: Agendamento) -> None:
    """Exclusão definitiva, para compromisso criado por engano.

    Um agendamento concluído não é excluído: ele é a origem de um atendimento do histórico.
    Para tirar um compromisso da agenda, o caminho é cancelar, que preserva o registro.
    """
    agendamento = _reler_com_trava(sessao, agendamento)
    if agendamento.status is StatusAgendamento.concluido:
        raise ValidacaoFalhou(
            "Um agendamento concluído faz parte do histórico do cliente e não pode ser excluído.",
            codigo="agendamento_concluido",
        )
    sessao.delete(agendamento)
    sessao.commit()
