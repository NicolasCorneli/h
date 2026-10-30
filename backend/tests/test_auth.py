"""RF01 — cadastro, login, renovação, perfil, ciência e exclusão de conta."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import SENHA


def test_cadastro_devolve_tokens_e_usuario(cliente_http: TestClient):
    resposta = cliente_http.post(
        "/api/v1/auth/registrar",
        json={"nome": "Ana Teste", "email": "ana@exemplo.com.br", "senha": SENHA},
    )
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["usuario"]["email"] == "ana@exemplo.com.br"
    assert corpo["tokens"]["accessToken"] and corpo["tokens"]["refreshToken"]
    assert "senha" not in str(corpo) and "senhaHash" not in str(corpo)


def test_email_repetido_da_conflito(cliente_http: TestClient):
    dados = {"nome": "Ana", "email": "repetida@exemplo.com.br", "senha": SENHA}
    assert cliente_http.post("/api/v1/auth/registrar", json=dados).status_code == 201
    repetida = cliente_http.post("/api/v1/auth/registrar", json=dados)
    assert repetida.status_code == 409
    assert repetida.json()["erro"]["codigo"] == "email_em_uso"


def test_email_e_normalizado_para_minusculas(cliente_http: TestClient):
    cliente_http.post(
        "/api/v1/auth/registrar",
        json={"nome": "Ana", "email": "Maiuscula@Exemplo.Com.Br", "senha": SENHA},
    )
    entrada = cliente_http.post(
        "/api/v1/auth/login", json={"email": "maiuscula@exemplo.com.br", "senha": SENHA}
    )
    assert entrada.status_code == 200


def test_senha_curta_e_recusada(cliente_http: TestClient):
    resposta = cliente_http.post(
        "/api/v1/auth/registrar",
        json={"nome": "Ana", "email": "curta@exemplo.com.br", "senha": "1234"},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "validacao"


def test_login_errado_nao_revela_se_o_email_existe(cliente_http: TestClient):
    cliente_http.post(
        "/api/v1/auth/registrar",
        json={"nome": "Ana", "email": "existe@exemplo.com.br", "senha": SENHA},
    )
    com_email = cliente_http.post(
        "/api/v1/auth/login", json={"email": "existe@exemplo.com.br", "senha": "errada-mas-longa"}
    )
    sem_email = cliente_http.post(
        "/api/v1/auth/login", json={"email": "naoexiste@exemplo.com.br", "senha": "errada-mas-longa"}
    )
    assert com_email.status_code == sem_email.status_code == 401
    assert com_email.json() == sem_email.json()


def test_renovacao_troca_o_refresh_por_um_acesso_novo(cliente_http: TestClient):
    criada = cliente_http.post(
        "/api/v1/auth/registrar",
        json={"nome": "Ana", "email": "renova@exemplo.com.br", "senha": SENHA},
    ).json()
    resposta = cliente_http.post(
        "/api/v1/auth/renovar", json={"refreshToken": criada["tokens"]["refreshToken"]}
    )
    assert resposta.status_code == 200
    novo = resposta.json()["accessToken"]
    perfil = cliente_http.get("/api/v1/usuarios/me", headers={"Authorization": f"Bearer {novo}"})
    assert perfil.status_code == 200


def test_access_token_nao_serve_para_renovar(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    token = cabecalhos["Authorization"].removeprefix("Bearer ")
    assert cliente_http.post("/api/v1/auth/renovar", json={"refreshToken": token}).status_code == 401


def test_rotas_protegidas_exigem_token(cliente_http: TestClient):
    for caminho in ("/api/v1/clientes", "/api/v1/usuarios/me", "/api/v1/agendamentos"):
        assert cliente_http.get(caminho).status_code == 401


def test_perfil_pode_ser_atualizado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.patch(
        "/api/v1/usuarios/me", headers=cabecalhos, json={"nome": "Nome Novo", "atuacao": "salão"}
    )
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Nome Novo"


def test_ciencia_comeca_pendente_e_pode_ser_registrada(cliente_http: TestClient, conta, versao_vigente):
    cabecalhos, _ = conta()
    antes = cliente_http.get("/api/v1/usuarios/me/ciencia", headers=cabecalhos).json()
    assert antes["aceita"] is False and antes["registradaEm"] is None

    criada = cliente_http.post("/api/v1/usuarios/me/ciencia", headers=cabecalhos)
    assert criada.status_code == 201
    depois = criada.json()
    assert depois["aceita"] is True and depois["registradaEm"]
    assert depois["versao"] == versao_vigente("profissional")


def test_exclusao_de_conta_exige_a_senha(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    errada = cliente_http.request(
        "DELETE", "/api/v1/usuarios/me", headers=cabecalhos, json={"senha": "nao-e-a-senha"}
    )
    assert errada.status_code == 403
    assert errada.json()["erro"]["codigo"] == "senha_incorreta"

    certa = cliente_http.request(
        "DELETE", "/api/v1/usuarios/me", headers=cabecalhos, json={"senha": SENHA}
    )
    assert certa.status_code == 204
    # O token continua criptograficamente válido, mas a conta não existe mais.
    assert cliente_http.get("/api/v1/usuarios/me", headers=cabecalhos).status_code == 401
