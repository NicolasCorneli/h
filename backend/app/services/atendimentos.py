"""Histórico de atendimentos (RF03).

O atendimento é independente do consentimento de imagem: pode existir sem simulação, e
continua existindo quando as imagens do cliente são apagadas.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.erros import NaoEncontrado, ValidacaoFalhou
from app.models import Atendimento, Usuario
from app.repositories import consultas
from app.services import agendamentos as servico_agenda
from app.schemas.atendimento import AtendimentoAtualizacao, AtendimentoEntrada


def _simulacao_valida(
    sessao: Session, usuario: Usuario, cliente_id: uuid.UUID, simulacao_id: uuid.UUID
) -> None:
    simulacao = consultas.simulacao_do_usuario(sessao, usuario.id, simulacao_id)
    if simulacao is None:
        raise NaoEncontrado("Simulação não encontrada.")
    if simulacao.cliente_id != cliente_id:
        raise ValidacaoFalhou(
            "A simulação pertence a outro cliente.", codigo="simulacao_de_outro_cliente"
        )


def criar(sessao: Session, usuario: Usuario, dados: AtendimentoEntrada) -> Atendimento:
    cliente = consultas.cliente_do_usuario(sessao, usuario.id, dados.cliente_id)
    if cliente is None:
        raise NaoEncontrado("Cliente não encontrado.")
    if dados.simulacao_id is not None:
        _simulacao_valida(sessao, usuario, cliente.id, dados.simulacao_id)

    # Com dia e hora, o dia vem do instante (no fuso do salão), como na conclusão de um
    # agendamento. Só com o dia, mantém-se o formato antigo, sem inventar a hora.
    if dados.realizado_em is not None:
        dia = servico_agenda.dia_do_atendimento(
            dados.realizado_em,
            "O horário do atendimento não pode estar no futuro.",
            "atendimento_no_futuro",
        )
    else:
        dia = dados.data_servico
        servico_agenda.validar_dia_nao_futuro(
            dia, "A data do atendimento não pode estar no futuro.", "atendimento_no_futuro"
        )

    # Atendimento avulso: sem agendamento de origem (`agendamento_id` vazio). Nenhum
    # agendamento é criado ou concluído para representá-lo.
    atendimento = Atendimento(
        cliente_id=cliente.id,
        usuario_id=usuario.id,
        simulacao_id=dados.simulacao_id,
        descricao=dados.descricao,
        data_servico=dia,
        realizado_em=dados.realizado_em,
        duracao_min=dados.duracao_min,
        observacoes=dados.observacoes,
    )
    sessao.add(atendimento)
    sessao.commit()
    sessao.refresh(atendimento)
    return atendimento


def atualizar(
    sessao: Session, usuario: Usuario, atendimento: Atendimento, dados: AtendimentoAtualizacao
) -> Atendimento:
    if dados.descricao is not None:
        atendimento.descricao = dados.descricao
    if "duracao_min" in dados.model_fields_set:
        atendimento.duracao_min = dados.duracao_min
    if dados.realizado_em is not None:
        # Dia e hora corrigidos juntos: o dia sai do instante, como no registro.
        atendimento.data_servico = servico_agenda.dia_do_atendimento(
            dados.realizado_em,
            "O horário do atendimento não pode estar no futuro.",
            "atendimento_no_futuro",
        )
        atendimento.realizado_em = dados.realizado_em
    elif dados.data_servico is not None and dados.data_servico != atendimento.data_servico:
        servico_agenda.validar_dia_nao_futuro(
            dados.data_servico,
            "A data do atendimento não pode estar no futuro.",
            "atendimento_no_futuro",
        )
        atendimento.data_servico = dados.data_servico
        # O horário real era de outro dia. Mantê-lo deixaria o registro dizendo duas datas
        # diferentes; o que se sabe agora é só o dia corrigido, sem a hora.
        if atendimento.realizado_em is not None:
            dia_registrado = atendimento.realizado_em.astimezone(obter_config().fuso).date()
            if dia_registrado != dados.data_servico:
                atendimento.realizado_em = None
    if dados.observacoes is not None:
        atendimento.observacoes = dados.observacoes
    if dados.desvincular_simulacao:
        atendimento.simulacao_id = None
    elif dados.simulacao_id is not None:
        _simulacao_valida(sessao, usuario, atendimento.cliente_id, dados.simulacao_id)
        atendimento.simulacao_id = dados.simulacao_id
    sessao.commit()
    sessao.refresh(atendimento)
    return atendimento


def excluir(sessao: Session, atendimento: Atendimento) -> None:
    """Remove um atendimento registrado por engano (cliente ou dia errado).

    Só o avulso. O que veio da agenda é o registro de um agendamento concluído: apagá-lo
    deixaria o compromisso "concluído" sem o serviço que o concluiu. Esse se corrige.
    """
    if atendimento.agendamento_id is not None:
        raise ValidacaoFalhou(
            "Este atendimento veio de um agendamento concluído e faz parte da agenda. "
            "Corrija os dados em vez de excluir.",
            codigo="atendimento_da_agenda",
        )
    sessao.delete(atendimento)
    sessao.commit()
