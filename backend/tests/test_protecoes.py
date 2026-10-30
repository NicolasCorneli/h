"""Proteções de borda: tamanho de corpo e força bruta no login."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core import protecoes
from tests.conftest import SENHA


def test_corpo_grande_demais_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    enorme = b"x" * (protecoes.LIMITE_CORPO_BYTES + 1024)
    resposta = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": "00000000-0000-0000-0000-000000000000", "corte": "Bob curto", "cor": "Loiro mel"},
        files={"foto": ("grande.jpg", enorme, "image/jpeg")},
    )
    assert resposta.status_code == 413
    assert resposta.json()["erro"]["codigo"] == "corpo_grande_demais"


def test_tentativas_de_login_sao_limitadas(cliente_http: TestClient, conta):
    _, usuario = conta()
    email = usuario["email"]

    respostas = [
        cliente_http.post(
            "/api/v1/auth/login", json={"email": email, "senha": "senha-errada-mas-longa"}
        ).status_code
        for _ in range(protecoes.MAX_TENTATIVAS + 2)
    ]
    assert respostas[0] == 401
    assert 429 in respostas, respostas
    assert respostas[-1] == 429

    bloqueada = cliente_http.post("/api/v1/auth/login", json={"email": email, "senha": SENHA})
    assert bloqueada.status_code == 429
    assert bloqueada.headers["Retry-After"]


def test_contador_zera_entre_testes(cliente_http: TestClient, conta):
    """Garante que o limite anterior não vaza para o próximo cenário."""
    _, usuario = conta()
    resposta = cliente_http.post(
        "/api/v1/auth/login", json={"email": usuario["email"], "senha": SENHA}
    )
    assert resposta.status_code == 200
