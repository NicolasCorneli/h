"""Contrato do provedor de simulação capilar.

O resto do backend conhece apenas estas peças: `EntradaSimulacao`, `SaidaSimulacao` e
`ProvedorIA`. Trocar de provedor é escrever outra implementação e mudar `AI_PROVIDER` no
ambiente; nenhum serviço, router ou modelo precisa mudar.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.ai.pedido import PedidoCapilar
    from app.services.ai.planos import Plano


@dataclass(frozen=True)
class EntradaSimulacao:
    imagem: bytes
    mime: str
    pedido: "PedidoCapilar"


@dataclass(frozen=True)
class SaidaSimulacao:
    imagem: bytes
    mime: str
    #: Identificação do modelo, registrada em `simulacoes.modelo_ia` para rastreabilidade.
    modelo: str
    tempo_ms: int
    #: O que foi pedido ao modelo (instrução ou opções), sem a imagem.
    instrucao: str = ""


class FalhaDoProvedor(Exception):
    """Indisponibilidade ou erro do serviço externo: vira 502 na API."""

    def __init__(self, mensagem: str, *, codigo: str = "provedor_indisponivel") -> None:
        super().__init__(mensagem)
        self.codigo = codigo


class ProvedorIA(ABC):
    #: Identificador curto gravado em `simulacoes.provedor`.
    nome: str = "indefinido"
    #: Identificação do modelo principal (diagnóstico).
    modelo: str = "indefinido"

    @abstractmethod
    def preparar(self, pedido: "PedidoCapilar") -> "Plano":
        """Escolhe o modelo e confere os parâmetros, antes de qualquer gasto.

        Levanta `FalhaDoProvedor` (credencial, modelo incompatível, provedor fora do ar) ou
        `ValidacaoFalhou` (descrição livre desligada na configuração).
        """

    @abstractmethod
    def gerar(self, entrada: EntradaSimulacao) -> SaidaSimulacao:
        """Devolve a imagem simulada ou levanta `FalhaDoProvedor`."""
