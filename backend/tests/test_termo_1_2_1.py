"""Termo 1.2.1: a 1.2 sem travessões (migration c8f2a6d4e913).

A revisão só de redação não pode mudar o conteúdo, porque quem aceitou a 1.2 não é chamado
a decidir de novo. Por isso o teste principal compara os textos: o da 1.2.1 tem de ser o
da 1.2 com exatamente as trocas de pontuação declaradas na migration, e nada mais.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import engine
from app.models import DecisaoConsentimento
from app.services.regras_consentimento import conteudo_da_versao, mesmo_conteudo, precisa_revalidar
from tests.test_consentimento import novo_cliente, registrar
from tests.test_termo_1_2 import termos

MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "c8f2a6d4e913_termo_1_2_1_sem_travessoes.py"
)


def migration():
    especificacao = importlib.util.spec_from_file_location("termo_1_2_1", MIGRATION)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def test_1_2_1_vigente_e_1_2_preservada(versao_vigente):
    for tipo in ("cliente", "profissional"):
        publicados = termos(tipo)
        assert versao_vigente(tipo) == "1.2.1"
        assert publicados["1.2"]["vigente"] is False
        assert sum(1 for t in publicados.values() if t["vigente"]) == 1


def test_so_a_pontuacao_mudou():
    trocas = migration().TROCAS
    for tipo in ("cliente", "profissional"):
        publicados = termos(tipo)
        antes, depois = publicados["1.2"]["secoes"], publicados["1.2.1"]["secoes"]
        assert [s["titulo"] for s in antes] == [s["titulo"] for s in depois]
        assert [s.get("destaque") for s in antes] == [s.get("destaque") for s in depois]
        for secao_antes, secao_depois in zip(antes, depois, strict=True):
            esperado = secao_antes["texto"]
            for de, para in trocas:
                esperado = esperado.replace(de, para)
            assert secao_depois["texto"] == esperado


def test_sem_travessao_nos_termos_vigentes():
    for tipo in ("cliente", "profissional"):
        vigente = next(t for t in termos(tipo).values() if t["vigente"])
        for secao in vigente["secoes"]:
            for campo in ("titulo", "texto"):
                assert "—" not in secao[campo] and "–" not in secao[campo], secao[campo]


def test_regra_de_versao():
    assert conteudo_da_versao("1.2.1") == "1.2"
    assert conteudo_da_versao("1.2") == "1.2"
    assert mesmo_conteudo("1.2", "1.2.1")
    assert not mesmo_conteudo("1.1", "1.2.1")
    aceito = DecisaoConsentimento.aceito
    assert precisa_revalidar(aceito, "1.2", "1.2.1") is False
    assert precisa_revalidar(aceito, "1.1", "1.2.1") is True
    assert precisa_revalidar(aceito, "1.2.1", "1.3") is True


def _vigencia(versao: str) -> None:
    with engine.begin() as conexao:
        conexao.execute(text("UPDATE termos SET vigente = false WHERE tipo = 'cliente'"))
        conexao.execute(
            text("UPDATE termos SET vigente = true WHERE tipo = 'cliente' AND versao = :v"), {"v": versao}
        )


def test_quem_aceitou_a_1_2_nao_precisa_revalidar(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    _vigencia("1.2")
    try:
        assert registrar(cliente_http, cabecalhos, cliente["id"]).status_code == 201
    finally:
        _vigencia("1.2.1")

    resumo = cliente_http.get(f"/api/v1/clientes/{cliente['id']}/consentimento", headers=cabecalhos).json()
    assert resumo["status"] == "aceito"
    assert resumo["revalidar"] is False
    assert resumo["bloqueio"] is None


def test_ciencia_do_profissional_na_1_2_continua_valendo(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    with engine.begin() as conexao:
        conexao.execute(text("UPDATE termos SET vigente = false WHERE tipo = 'profissional'"))
        conexao.execute(text("UPDATE termos SET vigente = true WHERE tipo = 'profissional' AND versao = '1.2'"))
    try:
        assert cliente_http.post("/api/v1/usuarios/me/ciencia", headers=cabecalhos).status_code in (200, 201)
    finally:
        with engine.begin() as conexao:
            conexao.execute(text("UPDATE termos SET vigente = false WHERE tipo = 'profissional'"))
            conexao.execute(
                text("UPDATE termos SET vigente = true WHERE tipo = 'profissional' AND versao = '1.2.1'")
            )
    ciencia = cliente_http.get("/api/v1/usuarios/me/ciencia", headers=cabecalhos)
    assert ciencia.status_code == 200, ciencia.text
    assert ciencia.json()["aceita"] is True
    assert ciencia.json()["versao"] == "1.2"
