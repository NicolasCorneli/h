"""RF02 — CRUD de clientes e isolamento entre contas."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from tests.fabricas import imagem_lisa


def criar_cliente(cliente_http: TestClient, cabecalhos, **extra):
    corpo = {"nome": "Marina Alves", "telefone": "(55) 99123-4567", "observacoes": "", **extra}
    return cliente_http.post("/api/v1/clientes", headers=cabecalhos, json=corpo)


def test_criar_e_listar(cliente_http: TestClient, conta):
    cabecalhos, usuario = conta()
    resposta = criar_cliente(cliente_http, cabecalhos)
    assert resposta.status_code == 201
    criado = resposta.json()
    assert criado["usuarioId"] == usuario["id"]
    assert criado["consentimento"]["status"] == "pendente"
    assert criado["consentimento"]["versaoVigente"] == "1.0"
    assert criado["fotoUri"] is None

    lista = cliente_http.get("/api/v1/clientes", headers=cabecalhos).json()
    assert [c["nome"] for c in lista] == ["Marina Alves"]


def test_nome_curto_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    assert criar_cliente(cliente_http, cabecalhos, nome="A").status_code == 422


def test_data_de_nascimento_no_futuro_e_recusada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = criar_cliente(cliente_http, cabecalhos, dataNascimento="2099-01-01")
    assert resposta.status_code == 422


def test_menor_de_idade_exige_responsavel_no_resumo(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    nascimento = date(date.today().year - 16, 4, 12).isoformat()
    criado = criar_cliente(
        cliente_http, cabecalhos, nome="Sofia Ramires", dataNascimento=nascimento
    ).json()
    assert criado["consentimento"]["exigeResponsavel"] is True


def test_busca_por_nome(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    criar_cliente(cliente_http, cabecalhos, nome="Marina Alves")
    criar_cliente(cliente_http, cabecalhos, nome="Bruno Tavares")
    achados = cliente_http.get(
        "/api/v1/clientes", headers=cabecalhos, params={"busca": "mari"}
    ).json()
    assert [c["nome"] for c in achados] == ["Marina Alves"]


def test_atualizar_e_limpar_data(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    criado = criar_cliente(cliente_http, cabecalhos, dataNascimento="1994-03-10").json()
    atualizado = cliente_http.patch(
        f"/api/v1/clientes/{criado['id']}",
        headers=cabecalhos,
        json={"observacoes": "Prefere tons quentes."},
    ).json()
    assert atualizado["observacoes"] == "Prefere tons quentes."
    assert atualizado["dataNascimento"] == "1994-03-10"

    limpo = cliente_http.patch(
        f"/api/v1/clientes/{criado['id']}",
        headers=cabecalhos,
        json={"limparDataNascimento": True},
    ).json()
    assert limpo["dataNascimento"] is None


def test_excluir_cliente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    criado = criar_cliente(cliente_http, cabecalhos).json()
    assert cliente_http.delete(f"/api/v1/clientes/{criado['id']}", headers=cabecalhos).status_code == 204
    assert cliente_http.get(f"/api/v1/clientes/{criado['id']}", headers=cabecalhos).status_code == 404


def test_cliente_de_outro_profissional_responde_404(cliente_http: TestClient, conta):
    cabecalhos_a, _ = conta()
    cabecalhos_b, _ = conta()
    do_a = criar_cliente(cliente_http, cabecalhos_a).json()

    for metodo, caminho in (
        ("GET", f"/api/v1/clientes/{do_a['id']}"),
        ("PATCH", f"/api/v1/clientes/{do_a['id']}"),
        ("DELETE", f"/api/v1/clientes/{do_a['id']}"),
        ("GET", f"/api/v1/clientes/{do_a['id']}/consentimento"),
        ("GET", f"/api/v1/clientes/{do_a['id']}/consentimentos"),
        ("GET", f"/api/v1/clientes/{do_a['id']}/historico"),
        ("GET", f"/api/v1/clientes/{do_a['id']}/simulacoes"),
        ("GET", f"/api/v1/clientes/{do_a['id']}/agendamentos"),
        ("DELETE", f"/api/v1/clientes/{do_a['id']}/simulacoes"),
    ):
        resposta = cliente_http.request(metodo, caminho, headers=cabecalhos_b, json={})
        assert resposta.status_code == 404, f"{metodo} {caminho} devolveu {resposta.status_code}"

    # E o cliente continua intacto para o dono.
    assert cliente_http.get(f"/api/v1/clientes/{do_a['id']}", headers=cabecalhos_a).status_code == 200


def test_foto_de_perfil_vai_e_volta(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    criado = criar_cliente(cliente_http, cabecalhos).json()

    enviada = cliente_http.post(
        f"/api/v1/clientes/{criado['id']}/foto",
        headers=cabecalhos,
        files={"arquivo": ("perfil.jpg", imagem_lisa(), "image/jpeg")},
    )
    assert enviada.status_code == 200
    uri = enviada.json()["fotoUri"]
    assert uri and "/api/v1/imagens/" in uri

    imagem = cliente_http.get(uri.replace("http://testserver", ""))
    assert imagem.status_code == 200
    assert imagem.headers["content-type"].startswith("image/")

    removida = cliente_http.delete(f"/api/v1/clientes/{criado['id']}/foto", headers=cabecalhos)
    assert removida.status_code == 204
    assert cliente_http.get(f"/api/v1/clientes/{criado['id']}", headers=cabecalhos).json()["fotoUri"] is None


def test_foto_invalida_e_recusada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    criado = criar_cliente(cliente_http, cabecalhos).json()
    resposta = cliente_http.post(
        f"/api/v1/clientes/{criado['id']}/foto",
        headers=cabecalhos,
        files={"arquivo": ("perfil.txt", b"nao sou imagem", "image/jpeg")},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "foto_recusada"
