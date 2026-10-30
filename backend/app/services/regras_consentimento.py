"""Regras de consentimento — funções puras, sem banco e sem HTTP.

São as mesmas regras que `espelho/src/services/consentService.ts` aplica na interface.
A diferença essencial: **aqui elas são controle de acesso**, não conveniência de tela.
Nenhuma imagem é enviada ao provedor de IA sem passar por `avaliar_captura`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.models.enums import DecisaoConsentimento, FaixaEtaria

StatusConsentimento = Literal["pendente", "aceito", "recusado", "revogado"]

MotivoBloqueio = Literal["pendente", "revalidar", "recusado", "revogado"]


def idade_em(data_nascimento: date | None, referencia: date | None = None) -> int | None:
    if data_nascimento is None:
        return None
    hoje = referencia or date.today()
    idade = hoje.year - data_nascimento.year
    aniversario_passou = (hoje.month, hoje.day) >= (data_nascimento.month, data_nascimento.day)
    return idade if aniversario_passou else idade - 1


def faixa_etaria(data_nascimento: date | None, referencia: date | None = None) -> FaixaEtaria:
    """LGPD, art. 14, §1º: criança (até 12 anos incompletos) exige consentimento de um dos
    pais ou do responsável legal. O projeto estende a exigência ao adolescente, por
    precaução — critério já adotado na interface e documentado no TCC.
    """
    idade = idade_em(data_nascimento, referencia)
    if idade is None:
        return FaixaEtaria.desconhecida
    if idade < 12:
        return FaixaEtaria.crianca
    if idade < 18:
        return FaixaEtaria.adolescente
    return FaixaEtaria.adulto


def exige_responsavel(data_nascimento: date | None, referencia: date | None = None) -> bool:
    return faixa_etaria(data_nascimento, referencia) in {
        FaixaEtaria.crianca,
        FaixaEtaria.adolescente,
    }


def status_de(decisao: DecisaoConsentimento | None) -> StatusConsentimento:
    """Ausência de registro é ausência de decisão: `pendente` não é persistido."""
    return decisao.value if decisao is not None else "pendente"  # type: ignore[return-value]


def precisa_revalidar(
    decisao: DecisaoConsentimento | None, versao_aceita: str | None, versao_vigente: str
) -> bool:
    """Aceite válido, mas dado sobre uma versão anterior do termo."""
    return decisao is DecisaoConsentimento.aceito and versao_aceita != versao_vigente


@dataclass(frozen=True)
class Bloqueio:
    motivo: MotivoBloqueio
    titulo: str
    descricao: str


def avaliar_captura(
    nome_cliente: str,
    decisao: DecisaoConsentimento | None,
    versao_aceita: str | None,
    versao_vigente: str,
) -> Bloqueio | None:
    """`None` significa liberado. Caso contrário, devolve o motivo do bloqueio.

    Mesmos textos da interface, para que a mensagem do servidor e a da tela coincidam.
    """
    primeiro_nome = nome_cliente.strip().split()[0] if nome_cliente.strip() else "O cliente"

    if decisao is None:
        return Bloqueio(
            motivo="pendente",
            titulo=f"{primeiro_nome} ainda não decidiu",
            descricao=(
                "Apresente o termo de uso de imagem para que o cliente leia e decida agora, "
                "sem sair do atendimento."
            ),
        )
    if decisao is DecisaoConsentimento.recusado:
        return Bloqueio(
            motivo="recusado",
            titulo=f"{primeiro_nome} não autorizou o uso da imagem",
            descricao=(
                "A câmera fica bloqueada para este cliente. Se ele mudou de ideia, apresente o "
                "termo novamente. Cadastro, histórico e agenda seguem funcionando normalmente."
            ),
        )
    if decisao is DecisaoConsentimento.revogado:
        return Bloqueio(
            motivo="revogado",
            titulo=f"{primeiro_nome} cancelou o consentimento",
            descricao=(
                "O consentimento dado antes foi cancelado a pedido do cliente. Só volte a "
                "fotografar se ele autorizar de novo."
            ),
        )
    if precisa_revalidar(decisao, versao_aceita, versao_vigente):
        return Bloqueio(
            motivo="revalidar",
            titulo="O termo mudou desde o último aceite",
            descricao=(
                f"{primeiro_nome} aceitou a versão {versao_aceita}; a atual é a "
                f"{versao_vigente}. Apresente o texto novo antes de fotografar."
            ),
        )
    return None
