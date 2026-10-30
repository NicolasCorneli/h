"""Enums do domínio.

Os valores são exatamente as strings usadas pelo aplicativo (`src/data/tipos.ts`), para
que o contrato da API não precise de tradução e a rastreabilidade com o TCC se mantenha.
"""

from __future__ import annotations

import enum


class TipoTermo(str, enum.Enum):
    cliente = "cliente"
    profissional = "profissional"


class DecisaoConsentimento(str, enum.Enum):
    aceito = "aceito"
    recusado = "recusado"
    revogado = "revogado"


class FormaObtencao(str, enum.Enum):
    tela_dispositivo = "tela_dispositivo"
    lido_em_voz_alta = "lido_em_voz_alta"
    termo_impresso = "termo_impresso"


class FaixaEtaria(str, enum.Enum):
    crianca = "crianca"
    adolescente = "adolescente"
    adulto = "adulto"
    desconhecida = "desconhecida"


class TipoImagem(str, enum.Enum):
    entrada = "entrada"
    saida = "saida"
    perfil = "perfil"


class StatusSimulacao(str, enum.Enum):
    processando = "processando"
    concluida = "concluida"
    falhou = "falhou"


class StatusAgendamento(str, enum.Enum):
    pendente = "pendente"
    confirmado = "confirmado"
    cancelado = "cancelado"
    concluido = "concluido"


#: Transições permitidas da agenda. `cancelado` e `concluido` são estados finais.
#:
#: `pendente → concluido` é permitido: confirmar é um passo anterior à visita, e o cliente
#: que chega sem ter sido confirmado continua sendo atendido. Exigir a confirmação antes
#: obrigaria o profissional a um toque sem significado só para poder registrar o serviço.
TRANSICOES_AGENDAMENTO: dict[StatusAgendamento, set[StatusAgendamento]] = {
    StatusAgendamento.pendente: {
        StatusAgendamento.confirmado,
        StatusAgendamento.cancelado,
        StatusAgendamento.concluido,
    },
    StatusAgendamento.confirmado: {StatusAgendamento.concluido, StatusAgendamento.cancelado},
    StatusAgendamento.cancelado: set(),
    StatusAgendamento.concluido: set(),
}
