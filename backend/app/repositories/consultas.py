"""Consultas reutilizadas pelos serviços.

Regra da casa: **toda** consulta que alcança dado de cliente recebe `usuario_id` e
filtra por ele. Não existe aqui nenhuma busca "por id" sem dono — é assim que o
isolamento entre contas deixa de depender da disciplina de quem escreve o router.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Agendamento,
    Atendimento,
    Ciencia,
    Cliente,
    Consentimento,
    Imagem,
    Simulacao,
    Termo,
    TipoImagem,
    TipoTermo,
    Usuario,
)


# --- Usuário e termos -----------------------------------------------------


def usuario_por_email(sessao: Session, email: str) -> Usuario | None:
    return sessao.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))


def termo_vigente(sessao: Session, tipo: TipoTermo) -> Termo | None:
    return sessao.scalar(select(Termo).where(Termo.tipo == tipo, Termo.vigente.is_(True)))


def termo_por_versao(sessao: Session, tipo: TipoTermo, versao: str) -> Termo | None:
    return sessao.scalar(select(Termo).where(Termo.tipo == tipo, Termo.versao == versao))


def ultima_ciencia(sessao: Session, usuario_id: uuid.UUID) -> Ciencia | None:
    return sessao.scalar(
        select(Ciencia)
        .where(Ciencia.usuario_id == usuario_id)
        .order_by(Ciencia.registrada_em.desc())
        .limit(1)
    )


# --- Clientes -------------------------------------------------------------


def clientes_do_usuario(sessao: Session, usuario_id: uuid.UUID, busca: str | None = None) -> list[Cliente]:
    consulta = select(Cliente).where(Cliente.usuario_id == usuario_id)
    termo = (busca or "").strip()
    if termo:
        # `%` e `_` são curingas do LIKE: sem escapar, buscar "_" devolvia a carteira toda.
        escapado = termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        consulta = consulta.where(Cliente.nome.ilike(f"%{escapado}%", escape="\\"))
    return list(sessao.scalars(consulta.order_by(Cliente.nome)))


def cliente_do_usuario(
    sessao: Session, usuario_id: uuid.UUID, cliente_id: uuid.UUID
) -> Cliente | None:
    return sessao.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.usuario_id == usuario_id)
    )


# --- Consentimentos -------------------------------------------------------


def ultimo_consentimento(sessao: Session, cliente_id: uuid.UUID) -> Consentimento | None:
    return sessao.scalar(
        select(Consentimento)
        .where(Consentimento.cliente_id == cliente_id)
        .order_by(Consentimento.registrado_em.desc(), Consentimento.id.desc())
        .limit(1)
    )


def historico_consentimentos(sessao: Session, cliente_id: uuid.UUID) -> list[Consentimento]:
    return list(
        sessao.scalars(
            select(Consentimento)
            .where(Consentimento.cliente_id == cliente_id)
            .order_by(Consentimento.registrado_em.desc(), Consentimento.id.desc())
        )
    )


def ultimos_consentimentos_por_cliente(
    sessao: Session, usuario_id: uuid.UUID
) -> dict[uuid.UUID, Consentimento]:
    """Último registro de cada cliente da carteira, em uma consulta só.

    Evita N+1 na lista de clientes, que mostra o selo de consentimento por linha.
    """
    linhas = sessao.execute(
        select(Consentimento)
        .join(Cliente, Cliente.id == Consentimento.cliente_id)
        .where(Cliente.usuario_id == usuario_id)
        .order_by(
            Consentimento.cliente_id,
            Consentimento.registrado_em.desc(),
            Consentimento.id.desc(),
        )
        .ext(distinct_on(Consentimento.cliente_id))
    ).scalars()
    return {registro.cliente_id: registro for registro in linhas}


# --- Simulações, atendimentos, agenda e imagens ---------------------------


#: As duas imagens vêm junto: cada simulação devolvida leva as URLs assinadas delas, e
#: sem isto seriam duas consultas a mais por simulação.
_COM_IMAGENS = (selectinload(Simulacao.img_entrada), selectinload(Simulacao.img_saida))


def simulacoes_do_cliente(sessao: Session, cliente_id: uuid.UUID) -> list[Simulacao]:
    return list(
        sessao.scalars(
            select(Simulacao)
            .where(Simulacao.cliente_id == cliente_id)
            .options(*_COM_IMAGENS)
            # A preferida primeiro; depois, da mais recente para a mais antiga. A mesma
            # ordem que o aplicativo usa (`ordenarSimulacoes`).
            .order_by(Simulacao.preferida.desc(), Simulacao.criado_em.desc())
        )
    )


def simulacoes_do_usuario(sessao: Session, usuario_id: uuid.UUID) -> list[Simulacao]:
    """Todas as simulações da conta, numa consulta só (antes: uma por cliente).

    Mesma ordem de antes: clientes por nome e, em cada um, a preferida primeiro.
    """
    return list(
        sessao.scalars(
            select(Simulacao)
            .join(Cliente, Cliente.id == Simulacao.cliente_id)
            .where(Cliente.usuario_id == usuario_id)
            .options(*_COM_IMAGENS)
            .order_by(
                Cliente.nome,
                Cliente.id,
                Simulacao.preferida.desc(),
                Simulacao.criado_em.desc(),
            )
        )
    )


def simulacao_do_usuario(
    sessao: Session, usuario_id: uuid.UUID, simulacao_id: uuid.UUID
) -> Simulacao | None:
    return sessao.scalar(
        select(Simulacao).where(Simulacao.id == simulacao_id, Simulacao.usuario_id == usuario_id)
    )


def atendimentos_do_usuario(
    sessao: Session, usuario_id: uuid.UUID, cliente_id: uuid.UUID | None = None
) -> list[Atendimento]:
    consulta = select(Atendimento).where(Atendimento.usuario_id == usuario_id)
    if cliente_id is not None:
        consulta = consulta.where(Atendimento.cliente_id == cliente_id)
    # No mesmo dia, o mais recente primeiro: pelo horário real e, sem ele, pela gravação.
    # Sem o desempate a ordem dentro do dia era a que o banco quisesse.
    return list(
        sessao.scalars(
            consulta.order_by(
                Atendimento.data_servico.desc(),
                Atendimento.realizado_em.desc().nulls_last(),
                Atendimento.criado_em.desc(),
            )
        )
    )


def atendimento_do_usuario(
    sessao: Session, usuario_id: uuid.UUID, atendimento_id: uuid.UUID
) -> Atendimento | None:
    return sessao.scalar(
        select(Atendimento).where(
            Atendimento.id == atendimento_id, Atendimento.usuario_id == usuario_id
        )
    )


def agendamentos_do_usuario(
    sessao: Session, usuario_id: uuid.UUID, cliente_id: uuid.UUID | None = None
) -> list[Agendamento]:
    consulta = (
        select(Agendamento)
        .where(Agendamento.usuario_id == usuario_id)
        # O atendimento vem junto: a lista expõe `atendimentoId` e, sem isto, faria uma
        # consulta por agendamento.
        .options(selectinload(Agendamento.atendimento))
    )
    if cliente_id is not None:
        consulta = consulta.where(Agendamento.cliente_id == cliente_id)
    return list(sessao.scalars(consulta.order_by(Agendamento.data_hora)))


def agendamento_do_usuario(
    sessao: Session, usuario_id: uuid.UUID, agendamento_id: uuid.UUID
) -> Agendamento | None:
    return sessao.scalar(
        select(Agendamento).where(
            Agendamento.id == agendamento_id, Agendamento.usuario_id == usuario_id
        )
    )


def imagem_do_usuario(
    sessao: Session, usuario_id: uuid.UUID, imagem_id: uuid.UUID
) -> Imagem | None:
    return sessao.scalar(
        select(Imagem).where(Imagem.id == imagem_id, Imagem.usuario_id == usuario_id)
    )


def foto_do_cliente(sessao: Session, cliente_id: uuid.UUID) -> Imagem | None:
    return sessao.scalar(
        select(Imagem).where(Imagem.cliente_id == cliente_id, Imagem.tipo == TipoImagem.perfil)
    )


def fotos_dos_clientes(sessao: Session, usuario_id: uuid.UUID) -> dict[uuid.UUID, Imagem]:
    """Foto de perfil de cada cliente da conta, numa consulta só (lista de clientes)."""
    linhas = sessao.scalars(
        select(Imagem).where(
            Imagem.usuario_id == usuario_id,
            Imagem.cliente_id.is_not(None),
            Imagem.tipo == TipoImagem.perfil,
        )
    )
    return {imagem.cliente_id: imagem for imagem in linhas if imagem.cliente_id is not None}


def imagens_do_cliente(sessao: Session, cliente_id: uuid.UUID) -> list[Imagem]:
    return list(sessao.scalars(select(Imagem).where(Imagem.cliente_id == cliente_id)))


def foto_do_usuario(sessao: Session, usuario_id: uuid.UUID) -> Imagem | None:
    """Foto do próprio profissional: imagem de perfil sem cliente."""
    return sessao.scalar(
        select(Imagem).where(
            Imagem.usuario_id == usuario_id,
            Imagem.cliente_id.is_(None),
            Imagem.tipo == TipoImagem.perfil,
        )
    )
