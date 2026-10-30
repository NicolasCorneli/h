"""Modelos do domínio.

A importação de todos aqui garante que `Base.metadata` esteja completa para o Alembic e
que as referências por string entre relacionamentos sejam resolvidas.
"""

from app.models.agendamento import Agendamento
from app.models.atendimento import Atendimento
from app.models.ciencia import Ciencia
from app.models.cliente import Cliente
from app.models.consentimento import Consentimento
from app.models.enums import (
    DecisaoConsentimento,
    FaixaEtaria,
    FormaObtencao,
    StatusAgendamento,
    StatusSimulacao,
    TipoImagem,
    TipoTermo,
)
from app.models.identidade_externa import IdentidadeExterna
from app.models.imagem import Imagem
from app.models.simulacao import Simulacao
from app.models.termo import Termo
from app.models.usuario import Usuario

__all__ = [
    "Agendamento",
    "Atendimento",
    "Ciencia",
    "Cliente",
    "Consentimento",
    "DecisaoConsentimento",
    "FaixaEtaria",
    "FormaObtencao",
    "IdentidadeExterna",
    "Imagem",
    "Simulacao",
    "StatusAgendamento",
    "StatusSimulacao",
    "Termo",
    "TipoImagem",
    "TipoTermo",
    "Usuario",
]
