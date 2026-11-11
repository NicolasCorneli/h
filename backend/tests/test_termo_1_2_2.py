"""Termo 1.2.2 do cliente: o tipo de cabelo desejado na lista do que é enviado
(migration d4b7a2e9f150).

A revisão não pode mudar o que o cliente autoriza, porque quem aceitou a 1.2 ou a 1.2.1 não
é chamado a decidir de novo. Por isso o teste principal compara os textos: o da 1.2.2 tem
de ser o da 1.2.1 com exatamente a troca declarada na migration, e nada mais.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from app.models import DecisaoConsentimento
from app.services.regras_consentimento import precisa_revalidar
from tests.test_consentimento import novo_cliente, registrar
from tests.test_termo_1_2 import termos, texto_de
from tests.test_termo_1_2_1 import _vigencia

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "d4b7a2e9f150_termo_1_2_2_tipo_de_cabelo.py"
)


def migration():
    especificacao = importlib.util.spec_from_file_location("termo_1_2_2", MIGRATION)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def test_1_2_2_vigente_so_para_o_cliente(versao_vigente):
    publicados = termos("cliente")
    assert versao_vigente("cliente") == "1.2.2"
    assert publicados["1.2.1"]["vigente"] is False
    assert sum(1 for t in publicados.values() if t["vigente"]) == 1
    # O termo do profissional não lista as escolhas enviadas: continua na 1.2.1.
    assert versao_vigente("profissional") == "1.2.1"
    assert "1.2.2" not in termos("profissional")


def test_so_a_lista_do_que_e_enviado_mudou():
    trocas = migration().TROCAS
    publicados = termos("cliente")
    antes, depois = publicados["1.2.1"]["secoes"], publicados["1.2.2"]["secoes"]
    assert [s["titulo"] for s in antes] == [s["titulo"] for s in depois]
    assert [s.get("destaque") for s in antes] == [s.get("destaque") for s in depois]
    trocadas = 0
    for secao_antes, secao_depois in zip(antes, depois, strict=True):
        esperado = secao_antes["texto"]
        for de, para in trocas:
            if de in esperado:
                trocadas += 1
            esperado = esperado.replace(de, para)
        assert secao_depois["texto"] == esperado
    assert trocadas == len(trocas)


def test_termo_diz_tudo_o_que_vai_e_o_que_fica():
    texto = texto_de(termos("cliente")["1.2.2"])
    assert "o corte, o estilo do corte, a cor e o tipo de cabelo desejado" in texto
    assert "gênero do corte" not in texto
    for dado in ("nome", "telefone", "data de nascimento", "observações"):
        assert dado in texto, f"o termo 1.2.2 não diz que {dado} fica de fora"
    for trecho in ("Replicate", "Google", "treinar", "fora do Brasil", "recuse"):
        assert trecho in texto


def test_regra_de_versao():
    aceito = DecisaoConsentimento.aceito
    assert precisa_revalidar(aceito, "1.2", "1.2.2") is False
    assert precisa_revalidar(aceito, "1.2.1", "1.2.2") is False
    assert precisa_revalidar(aceito, "1.1", "1.2.2") is True


def test_quem_aceitou_a_1_2_1_nao_precisa_revalidar(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    anterior = _vigencia("1.2.1")
    try:
        assert registrar(cliente_http, cabecalhos, cliente["id"]).status_code == 201
    finally:
        _vigencia(anterior)

    resumo = cliente_http.get(f"/api/v1/clientes/{cliente['id']}/consentimento", headers=cabecalhos).json()
    assert resumo["status"] == "aceito"
    assert resumo["revalidar"] is False
    assert resumo["bloqueio"] is None


def test_aceite_novo_fica_ligado_a_1_2_2(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    resposta = registrar(cliente_http, cabecalhos, cliente["id"])
    assert resposta.status_code == 201, resposta.text
    resumo = cliente_http.get(f"/api/v1/clientes/{cliente['id']}/consentimento", headers=cabecalhos).json()
    assert resumo["status"] == "aceito"
    assert resumo["revalidar"] is False
    assert resumo["versaoVigente"] == "1.2.2"
    assert resumo["registro"]["versaoTermo"] == "1.2.2"
