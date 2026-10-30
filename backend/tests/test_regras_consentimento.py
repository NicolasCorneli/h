"""Testes unitários das regras de consentimento — sem banco, sem HTTP."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.enums import DecisaoConsentimento, FaixaEtaria
from app.services.regras_consentimento import (
    avaliar_captura,
    exige_responsavel,
    faixa_etaria,
    idade_em,
    precisa_revalidar,
    status_de,
)

HOJE = date(2026, 10, 2)


@pytest.mark.parametrize(
    ("nascimento", "idade"),
    [
        (date(2000, 10, 2), 26),  # aniversário é hoje
        (date(2000, 10, 3), 25),  # aniversário é amanhã
        (date(2008, 1, 1), 18),
        (date(2008, 12, 31), 17),
        (None, None),
    ],
)
def test_idade_em(nascimento, idade):
    assert idade_em(nascimento, HOJE) == idade


@pytest.mark.parametrize(
    ("idade_anos", "faixa"),
    [
        (5, FaixaEtaria.crianca),
        (11, FaixaEtaria.crianca),
        (12, FaixaEtaria.adolescente),
        (17, FaixaEtaria.adolescente),
        (18, FaixaEtaria.adulto),
        (40, FaixaEtaria.adulto),
    ],
)
def test_faixa_etaria(idade_anos, faixa):
    nascimento = date(HOJE.year - idade_anos, 1, 1)
    assert faixa_etaria(nascimento, HOJE) is faixa


def test_faixa_desconhecida_sem_data():
    assert faixa_etaria(None, HOJE) is FaixaEtaria.desconhecida
    # Sem data não há como inferir idade: a exigência de responsável não se aplica.
    assert exige_responsavel(None, HOJE) is False


@pytest.mark.parametrize(
    ("idade_anos", "exige"),
    [(8, True), (17, True), (18, False), (30, False)],
)
def test_exige_responsavel(idade_anos, exige):
    assert exige_responsavel(date(HOJE.year - idade_anos, 1, 1), HOJE) is exige


def test_status_sem_registro_e_pendente():
    assert status_de(None) == "pendente"
    assert status_de(DecisaoConsentimento.revogado) == "revogado"


def test_revalidacao_depende_da_versao():
    assert precisa_revalidar(DecisaoConsentimento.aceito, "0.9", "1.0") is True
    assert precisa_revalidar(DecisaoConsentimento.aceito, "1.0", "1.0") is False
    # Recusa e revogação não "revalidam": continuam bloqueando.
    assert precisa_revalidar(DecisaoConsentimento.recusado, "0.9", "1.0") is False


def test_captura_liberada_apenas_com_aceite_vigente():
    assert avaliar_captura("Marina Alves", DecisaoConsentimento.aceito, "1.0", "1.0") is None


@pytest.mark.parametrize(
    ("decisao", "versao", "motivo"),
    [
        (None, None, "pendente"),
        (DecisaoConsentimento.recusado, "1.0", "recusado"),
        (DecisaoConsentimento.revogado, "1.0", "revogado"),
        (DecisaoConsentimento.aceito, "0.9", "revalidar"),
    ],
)
def test_captura_bloqueada(decisao, versao, motivo):
    bloqueio = avaliar_captura("Marina Alves", decisao, versao, "1.0")
    assert bloqueio is not None
    assert bloqueio.motivo == motivo
    assert bloqueio.titulo and bloqueio.descricao


def test_mensagem_usa_o_primeiro_nome():
    bloqueio = avaliar_captura("Marina Alves", None, None, "1.0")
    assert bloqueio is not None
    assert bloqueio.titulo.startswith("Marina ")
