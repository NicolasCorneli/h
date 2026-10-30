from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.base import DuracaoOpcional, ModeloBase


class AtendimentoEntrada(ModeloBase):
    """Atendimento registrado direto, sem agendamento (o cliente chegou sem marcar).

    Informe `realizado_em` (dia e hora em que aconteceu; o dia é calculado no fuso do
    salão) ou, como antes, só `data_servico`. Um dos dois é obrigatório.
    """

    cliente_id: uuid.UUID
    descricao: str = Field(min_length=2, max_length=160)
    data_servico: date | None = None
    realizado_em: AwareDatetime | None = None
    duracao_min: DuracaoOpcional = None
    observacoes: str = Field(default="", max_length=4000)
    #: Opcional: um atendimento pode existir sem simulação prévia.
    simulacao_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _quando(self) -> "AtendimentoEntrada":
        if self.data_servico is None and self.realizado_em is None:
            raise ValueError("informe quando o atendimento aconteceu (realizadoEm ou dataServico)")
        return self


class AtendimentoAtualizacao(ModeloBase):
    """Correção de um atendimento já registrado. Campo ausente: não muda.

    `realizado_em` corrige o dia e a hora juntos (o dia é recalculado no fuso do salão);
    `data_servico` sozinho corrige só o dia, nos registros sem hora. `duracao_min` enviado
    como `null` apaga a duração.
    """

    descricao: str | None = Field(default=None, min_length=2, max_length=160)
    data_servico: date | None = None
    realizado_em: AwareDatetime | None = None
    duracao_min: DuracaoOpcional = None
    observacoes: str | None = Field(default=None, max_length=4000)
    simulacao_id: uuid.UUID | None = None
    desvincular_simulacao: bool = False


class AtendimentoOut(ModeloBase):
    id: uuid.UUID
    cliente_id: uuid.UUID
    usuario_id: uuid.UUID
    simulacao_id: uuid.UUID | None
    #: O agendamento de origem. Vazio nos atendimentos avulsos e nos antigos.
    agendamento_id: uuid.UUID | None
    descricao: str
    #: O dia em que o serviço aconteceu.
    data_servico: date
    #: O instante real da conclusão. Vazio nos registros antigos.
    realizado_em: datetime | None
    #: Quanto durou, quando informado.
    duracao_min: int | None
    observacoes: str
    criado_em: datetime
