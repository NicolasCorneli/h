from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AwareDatetime, Field

from app.models.enums import StatusAgendamento
from app.schemas.base import DuracaoOpcional, ModeloBase

# `AwareDatetime`, e não `datetime`: um horário sem fuso é ambíguo. "2026-10-24T10:00"
# pode ser 10h em Brasília ou 10h em Greenwich, três horas de diferença — e compará-lo
# com o instante atual, que tem fuso, levanta erro no Python. O aplicativo sempre envia o
# fuso (`toISOString()`); o servidor passa a exigir.


class AgendamentoEntrada(ModeloBase):
    cliente_id: uuid.UUID
    data_hora: AwareDatetime
    servico: str = Field(min_length=2, max_length=80)
    #: Opcional. Sem duração, o compromisso ocupa só o horário de início na agenda.
    duracao_min: DuracaoOpcional = None
    observacoes: str = Field(default="", max_length=2000)
    lembrete: bool = False


class AgendamentoAtualizacao(ModeloBase):
    #: Trocar o cliente corrige um agendamento feito no nome errado. A posse do cliente
    #: novo é conferida no servidor, como em qualquer outro identificador.
    cliente_id: uuid.UUID | None = None
    data_hora: AwareDatetime | None = None
    servico: str | None = Field(default=None, min_length=2, max_length=80)
    #: Ausente: não muda. `null` enviado de propósito: apaga a duração prevista.
    duracao_min: DuracaoOpcional = None
    observacoes: str | None = Field(default=None, max_length=2000)
    lembrete: bool | None = None


class MudancaDeStatus(ModeloBase):
    status: StatusAgendamento


class Cancelamento(ModeloBase):
    #: Opcional: nem todo cancelamento tem motivo que valha registrar.
    motivo: str = Field(default="", max_length=300)


class Conclusao(ModeloBase):
    """O que se informa ao concluir. Tudo opcional, com padrão sensato.

    - `realizado_em`: quando o atendimento de fato aconteceu (pode diferir do horário
      marcado). Padrão: agora. Não pode ser no futuro.
    - `descricao`: o serviço executado. Padrão: o que estava previsto no agendamento.
    - `observacoes`: anotações do atendimento.
    - `simulacao_id`: a simulação que guiou o serviço, se houver.
    """

    realizado_em: AwareDatetime | None = None
    descricao: str | None = Field(default=None, min_length=2, max_length=160)
    observacoes: str | None = Field(default=None, max_length=4000)
    simulacao_id: uuid.UUID | None = None
    #: Quanto o atendimento durou. Opcional; o aplicativo sugere a duração prevista.
    duracao_min: DuracaoOpcional = None


class AgendamentoOut(ModeloBase):
    id: uuid.UUID
    cliente_id: uuid.UUID
    usuario_id: uuid.UUID
    data_hora: datetime
    servico: str
    duracao_min: int | None
    status: StatusAgendamento
    observacoes: str
    lembrete: bool
    cancelado_em: datetime | None
    motivo_cancelamento: str
    #: O atendimento gerado na conclusão, quando houver.
    atendimento_id: uuid.UUID | None


class ConclusaoOut(ModeloBase):
    """Resposta da conclusão: o compromisso atualizado e o atendimento que ele gerou.

    Os dois juntos, para a tela atualizar agenda e histórico com uma requisição só.
    """

    agendamento: AgendamentoOut
    atendimento: "AtendimentoOut"


from app.schemas.atendimento import AtendimentoOut  # noqa: E402

ConclusaoOut.model_rebuild()
