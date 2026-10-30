"""Entradas hostis: injeção, travessia de caminho e conteúdo disfarçado."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.services.storage.base import ChaveInvalida, montar_chave, validar_chave
from app.models.enums import TipoImagem


def test_busca_com_aspas_nao_quebra_a_consulta(cliente_http: TestClient, conta):
    """O ORM parametriza o valor: a aspa é texto, não SQL."""
    cabecalhos, _ = conta()
    cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "O'Brien Souza", "telefone": "1"}
    )

    achados = cliente_http.get(
        "/api/v1/clientes", headers=cabecalhos, params={"busca": "o'brien"}
    )
    assert achados.status_code == 200
    assert [c["nome"] for c in achados.json()] == ["O'Brien Souza"]

    injecao = cliente_http.get(
        "/api/v1/clientes", headers=cabecalhos, params={"busca": "'; DROP TABLE clientes; --"}
    )
    assert injecao.status_code == 200
    assert injecao.json() == []
    # A tabela continua lá.
    assert cliente_http.get("/api/v1/clientes", headers=cabecalhos).status_code == 200


def test_identificador_invalido_na_url(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.get("/api/v1/clientes/../../etc/passwd", headers=cabecalhos)
    assert resposta.status_code in {404, 422}


@pytest.mark.parametrize(
    "chave",
    [
        "../../etc/passwd",
        "usuarios/../../segredo.jpg",
        "/etc/passwd",
        "usuarios/x/",
        "",
    ],
)
def test_chaves_de_objeto_perigosas_sao_recusadas(chave):
    with pytest.raises(ChaveInvalida):
        validar_chave(chave)


def test_chave_gerada_nao_usa_nome_enviado():
    """A chave nasce de UUIDs: o nome do arquivo do cliente não participa."""
    usuario, cliente, simulacao = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    chave = montar_chave(usuario, cliente, TipoImagem.entrada, "image/jpeg", simulacao)
    assert chave.startswith(f"usuarios/{usuario}/clientes/{cliente}/simulacoes/{simulacao}/")
    assert chave.endswith(".jpg")
    assert ".." not in chave


def test_executavel_disfarcado_de_imagem(cliente_http: TestClient, conta):
    """Extensão e content-type dizem JPEG; o conteúdo não é imagem."""
    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Teste Silva", "telefone": "1"}
    ).json()

    resposta = cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/foto",
        headers=cabecalhos,
        files={"arquivo": ("foto.jpg", b"#!/bin/sh\nrm -rf /\n", "image/jpeg")},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "foto_recusada"


def test_campos_longos_sao_recusados(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.post(
        "/api/v1/clientes",
        headers=cabecalhos,
        json={"nome": "A" * 500, "telefone": "1"},
    )
    assert resposta.status_code == 422


def test_resposta_de_erro_nao_traz_detalhe_interno(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.get(f"/api/v1/clientes/{uuid.uuid4()}", headers=cabecalhos)
    corpo = resposta.text
    assert resposta.status_code == 404
    for vazamento in ("Traceback", "sqlalchemy", "psycopg", "SELECT"):
        assert vazamento not in corpo
