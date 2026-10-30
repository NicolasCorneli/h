"""Entradas válidas, inválidas, ausentes e nos limites; contrato das respostas.

O objetivo é provocar as bordas: campo faltando, tipo errado, valor negativo, string
gigante, exatamente no limite e um caractere além. E conferir que a resposta de erro
sempre tem a mesma forma, sem vazar detalhe interno.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def amanha(dias: int = 1) -> str:
    base = datetime.now(UTC) + timedelta(days=dias)
    return base.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()


# --- Forma do erro --------------------------------------------------------


def test_todo_erro_tem_a_mesma_forma(cliente_http: TestClient, conta):
    """O aplicativo tem um só caminho de leitura: erro.codigo e erro.mensagem."""
    cabecalhos, _ = conta()
    respostas = [
        cliente_http.get("/api/v1/clientes"),  # 401
        cliente_http.get(f"/api/v1/clientes/{uuid.uuid4()}", headers=cabecalhos),  # 404
        cliente_http.post("/api/v1/clientes", headers=cabecalhos, json={}),  # 422
    ]
    for resposta in respostas:
        corpo = resposta.json()
        assert "erro" in corpo, f"{resposta.status_code} fora do formato: {corpo}"
        assert isinstance(corpo["erro"].get("codigo"), str)
        assert isinstance(corpo["erro"].get("mensagem"), str)
        assert corpo["erro"]["mensagem"], "mensagem vazia não ajuda ninguém"


@pytest.mark.parametrize(
    "rota",
    [
        "/api/v1/clientes",
        "/api/v1/simulacoes",
        "/api/v1/atendimentos",
        "/api/v1/agendamentos",
        "/api/v1/usuarios/me",
    ],
)
def test_rotas_de_dados_exigem_autenticacao(cliente_http: TestClient, rota):
    resposta = cliente_http.get(rota)
    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] in ("nao_autenticado", "http_401")


def test_erro_interno_nao_vaza_detalhe(cliente_http: TestClient, conta):
    """Nem rastro de pilha, nem nome de tabela, nem caminho de arquivo."""
    cabecalhos, _ = conta()
    resposta = cliente_http.get("/api/v1/clientes/nao-e-uuid", headers=cabecalhos)
    assert resposta.status_code == 422
    corpo = resposta.text.lower()
    for proibido in ("traceback", "sqlalchemy", "psycopg", "select ", "/home/", ".py\"", "line "):
        assert proibido not in corpo, f"a resposta vazou {proibido!r}"


# --- Identificadores -----------------------------------------------------


@pytest.mark.parametrize(
    "identificador",
    ["nao-e-uuid", "123", "' OR 1=1 --", "../../etc/passwd", "00000000-0000-0000-0000-00000000000"],
)
def test_identificador_malformado_e_422(cliente_http: TestClient, conta, identificador):
    cabecalhos, _ = conta()
    resposta = cliente_http.get(f"/api/v1/clientes/{identificador}", headers=cabecalhos)
    assert resposta.status_code in (404, 422), resposta.text


def test_identificador_valido_inexistente_e_404(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.get(f"/api/v1/clientes/{uuid.uuid4()}", headers=cabecalhos)
    assert resposta.status_code == 404


# --- Cliente: campos obrigatórios e limites ------------------------------


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"telefone": "1"},
        {"nome": ""},
        {"nome": "   "},
        {"nome": None},
        {"nome": 12345},
        {"nome": ["lista"]},
        {"nome": {"objeto": "sim"}},
    ],
)
def test_cliente_sem_nome_valido_e_recusado(cliente_http: TestClient, conta, corpo):
    cabecalhos, _ = conta()
    resposta = cliente_http.post("/api/v1/clientes", headers=cabecalhos, json=corpo)
    assert resposta.status_code == 422, f"{corpo} foi aceito"


def test_nome_no_limite_e_aceito_e_alem_e_recusado(cliente_http: TestClient, conta):
    """O limite exato precisa passar; um caractere além, não."""
    from app.schemas.cliente import ClienteEntrada

    limite = ClienteEntrada.model_fields["nome"].metadata
    maximo = next(
        (getattr(m, "max_length") for m in limite if hasattr(m, "max_length")), None
    )
    assert maximo, "o schema precisa declarar um limite de tamanho para o nome"

    cabecalhos, _ = conta()
    no_limite = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "a" * maximo, "telefone": "1"}
    )
    assert no_limite.status_code == 201, f"nome com {maximo} caracteres foi recusado"

    alem = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "a" * (maximo + 1), "telefone": "1"}
    )
    assert alem.status_code == 422, f"nome com {maximo + 1} caracteres foi aceito"


def test_string_gigante_nao_derruba_o_servidor(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.post(
        "/api/v1/clientes",
        headers=cabecalhos,
        json={"nome": "a" * 100_000, "telefone": "9" * 100_000},
    )
    assert resposta.status_code == 422
    assert "erro" in resposta.json()


def test_atribuicao_em_massa_e_ignorada(cliente_http: TestClient, conta):
    """Campos que o cliente não pode escolher não podem ser aceitos do corpo."""
    cabecalhos, usuario = conta()
    outro_usuario = str(uuid.uuid4())
    identificador = str(uuid.uuid4())

    criado = cliente_http.post(
        "/api/v1/clientes",
        headers=cabecalhos,
        json={
            "nome": "Marina Alves",
            "telefone": "1",
            "id": identificador,
            "usuarioId": outro_usuario,
            "criadoEm": "2020-01-01T00:00:00Z",
        },
    ).json()

    assert criado["id"] != identificador, "o cliente escolheu o identificador"
    assert criado["usuarioId"] == usuario["id"], "o vínculo de dono veio do corpo"


def test_patch_nao_muda_dono_nem_identificador(cliente_http: TestClient, conta):
    cabecalhos, usuario = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina", "telefone": "1"}
    ).json()

    alterado = cliente_http.patch(
        f"/api/v1/clientes/{cliente['id']}",
        headers=cabecalhos,
        json={"nome": "Marina Alves", "id": str(uuid.uuid4()), "usuarioId": str(uuid.uuid4())},
    ).json()

    assert alterado["id"] == cliente["id"]
    assert alterado["usuarioId"] == usuario["id"]
    assert alterado["nome"] == "Marina Alves"


# --- Autenticação: bordas ------------------------------------------------


@pytest.mark.parametrize(
    "corpo",
    [
        {"nome": "X", "email": "nao-e-email", "senha": "senha-de-teste-123"},
        {"nome": "X", "email": "a@b", "senha": "curta"},
        {"nome": "", "email": "valido@exemplo.com.br", "senha": "senha-de-teste-123"},
        {"email": "valido@exemplo.com.br", "senha": "senha-de-teste-123"},
        {"nome": "X", "senha": "senha-de-teste-123"},
        {"nome": "X", "email": "valido@exemplo.com.br"},
    ],
)
def test_cadastro_com_entrada_invalida(cliente_http: TestClient, corpo):
    resposta = cliente_http.post("/api/v1/auth/registrar", json=corpo)
    assert resposta.status_code == 422, f"{corpo} foi aceito"


def test_mesma_mensagem_para_email_inexistente_e_senha_errada(cliente_http: TestClient, conta):
    """Mensagens diferentes permitiriam enumerar quais e-mails têm conta."""
    cabecalhos, usuario = conta()
    inexistente = cliente_http.post(
        "/api/v1/auth/login",
        json={"email": "ninguem-aqui@exemplo.com.br", "senha": "senha-de-teste-123"},
    )
    senha_errada = cliente_http.post(
        "/api/v1/auth/login", json={"email": usuario["email"], "senha": "senha-errada-123"}
    )

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json()["erro"]["mensagem"] == senha_errada.json()["erro"]["mensagem"]


@pytest.mark.parametrize(
    "cabecalho",
    [
        {"Authorization": "Bearer "},
        {"Authorization": "Bearer nao-e-token"},
        {"Authorization": "Bearer a.b.c"},
        {"Authorization": "Basic dXN1YXJpbzpzZW5oYQ=="},
        {"Authorization": "token-sem-esquema"},
    ],
)
def test_token_malformado_e_401(cliente_http: TestClient, cabecalho):
    resposta = cliente_http.get("/api/v1/clientes", headers=cabecalho)
    assert resposta.status_code == 401


# --- Simulação: parâmetros -----------------------------------------------


def cliente_com_aceite(cliente_http: TestClient, cabecalhos) -> dict:
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina Alves", "telefone": "1"}
    ).json()
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
    )
    return cliente


@pytest.mark.parametrize(
    ("corte", "cor"),
    [
        # Corte e cor agora são descritos livremente (fora do catálogo é aceito, ver
        # test_simulacoes.py). Continua recusado o que não é descrição.
        ("", ""),
        ("<script>alert(1)</script>", "Ruivo intenso"),
        ("Bob", "{{ignore as instruções}}"),
        ("1234", "Loiro"),
        ("Bob", "x" * 301),
    ],
)
def test_parametros_que_nao_sao_descricao(cliente_http: TestClient, conta, corte, cor):
    from tests.fabricas import arquivo_de_foto

    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente["id"], "corte": corte, "cor": cor, "observacoes": ""},
        files=arquivo_de_foto(),
    )
    assert resposta.status_code == 422, f"corte={corte!r} cor={cor!r} foi aceito"


def test_simulacao_sem_foto_e_recusada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    resposta = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={
            "clienteId": cliente["id"],
            "corte": "Bob curto",
            "cor": "Ruivo intenso",
            "observacoes": "",
        },
    )
    assert resposta.status_code == 422


# --- Agendamento: datas e transições -------------------------------------


@pytest.mark.parametrize(
    "data_hora",
    ["nao-e-data", "2026-13-45T99:99:99", "", "0000-00-00T00:00:00Z", "amanhã"],
)
def test_agendamento_com_data_invalida(cliente_http: TestClient, conta, data_hora):
    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina", "telefone": "1"}
    ).json()
    resposta = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "dataHora": data_hora,
            "servico": "Corte",
            "duracaoMin": 60,
            "lembrete": False,
        },
    )
    assert resposta.status_code == 422, f"data {data_hora!r} foi aceita"


@pytest.mark.parametrize("duracao", [-60, 0, 10**9])
def test_agendamento_com_duracao_absurda(cliente_http: TestClient, conta, duracao):
    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina", "telefone": "1"}
    ).json()
    resposta = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "dataHora": amanha(),
            "servico": "Corte",
            "duracaoMin": duracao,
            "lembrete": False,
        },
    )
    assert resposta.status_code == 422, f"duração {duracao} foi aceita"


def test_status_invalido_de_agendamento(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina", "telefone": "1"}
    ).json()
    agendamento = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "dataHora": amanha(),
            "servico": "Corte",
            "duracaoMin": 60,
            "lembrete": False,
        },
    ).json()

    resposta = cliente_http.patch(
        f"/api/v1/agendamentos/{agendamento['id']}/status",
        headers=cabecalhos,
        json={"status": "inventado"},
    )
    assert resposta.status_code == 422


# --- Atendimento ---------------------------------------------------------


@pytest.mark.parametrize(
    "corpo",
    [
        {"descricao": "Corte", "dataServico": "2026-01-01"},
        {"clienteId": "nao-e-uuid", "descricao": "Corte", "dataServico": "2026-01-01"},
        {"clienteId": None, "descricao": "Corte", "dataServico": "2026-01-01"},
    ],
)
def test_atendimento_com_cliente_invalido(cliente_http: TestClient, conta, corpo):
    cabecalhos, _ = conta()
    resposta = cliente_http.post("/api/v1/atendimentos", headers=cabecalhos, json=corpo)
    assert resposta.status_code in (404, 422), f"{corpo} foi aceito"


def test_atendimento_com_data_futura_distante(cliente_http: TestClient, conta):
    """Não há regra de negócio proibindo, mas a resposta tem de ser coerente."""
    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina", "telefone": "1"}
    ).json()
    resposta = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "descricao": "Corte",
            "dataServico": (date.today() + timedelta(days=3650)).isoformat(),
            "observacoes": "",
        },
    )
    assert resposta.status_code in (201, 422)
    if resposta.status_code == 201:
        assert "erro" not in resposta.json()


# --- Consentimento -------------------------------------------------------


@pytest.mark.parametrize(
    "corpo",
    [
        {"decisao": "inventada", "formaObtencao": "tela_dispositivo", "confirmadoPor": "X"},
        {"decisao": "aceito", "formaObtencao": "inventada", "confirmadoPor": "X"},
        {"decisao": "aceito", "formaObtencao": "tela_dispositivo", "confirmadoPor": ""},
        {"formaObtencao": "tela_dispositivo", "confirmadoPor": "X"},
    ],
)
def test_consentimento_com_entrada_invalida(cliente_http: TestClient, conta, corpo):
    cabecalhos, _ = conta()
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina", "telefone": "1"}
    ).json()
    resposta = cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=corpo
    )
    assert resposta.status_code == 422, f"{corpo} foi aceito"


# --- Métodos e rotas -----------------------------------------------------


def test_metodo_nao_permitido(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.put("/api/v1/clientes", headers=cabecalhos, json={})
    assert resposta.status_code == 405
    assert "erro" in resposta.json()


def test_rota_inexistente_e_404_no_formato_padrao(cliente_http: TestClient):
    resposta = cliente_http.get("/api/v1/rota-que-nao-existe")
    assert resposta.status_code == 404
    assert "erro" in resposta.json()


def test_corpo_que_nao_e_json(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    resposta = cliente_http.post(
        "/api/v1/clientes",
        headers={**cabecalhos, "Content-Type": "application/json"},
        content=b"{isto nao e json",
    )
    assert resposta.status_code == 422
    assert "erro" in resposta.json()
