"""RF03 e RF06 — histórico de atendimentos e agenda."""

from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def novo_cliente(cliente_http: TestClient, cabecalhos, nome: str = "Marina Alves") -> dict:
    return cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": nome, "telefone": "1"}
    ).json()


def amanha(hora: int = 14, minuto: int = 30) -> str:
    base = datetime.now(UTC) + timedelta(days=1)
    return base.replace(hour=hora, minute=minuto, second=0, microsecond=0).isoformat()


# --- Atendimentos ---------------------------------------------------------


def test_atendimento_sem_simulacao(cliente_http: TestClient, conta):
    cabecalhos, usuario = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    resposta = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "descricao": "Hidratação",
            "dataServico": date.today().isoformat(),
            "observacoes": "Sem simulação.",
        },
    )
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["simulacaoId"] is None
    assert corpo["usuarioId"] == usuario["id"]


def test_atendimento_vinculado_a_simulacao(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
    )
    simulacao = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente["id"], "corte": "Bob curto", "cor": "Loiro mel"},
        files=arquivo_de_foto(),
    ).json()
    for _ in range(60):
        estado = cliente_http.get(f"/api/v1/simulacoes/{simulacao['id']}", headers=cabecalhos).json()
        if estado["status"] != "processando":
            break
        time.sleep(0.2)

    criado = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "descricao": "Coloração seguindo a simulação",
            "dataServico": date.today().isoformat(),
            "simulacaoId": simulacao["id"],
        },
    )
    assert criado.status_code == 201
    assert criado.json()["simulacaoId"] == simulacao["id"]


def test_simulacao_de_outro_cliente_nao_vincula(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    um = novo_cliente(cliente_http, cabecalhos, "Marina Alves")
    outro = novo_cliente(cliente_http, cabecalhos, "Bruno Tavares")
    cliente_http.post(f"/api/v1/clientes/{um['id']}/consentimentos", headers=cabecalhos, json=ACEITE)
    simulacao = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": um["id"], "corte": "Bob curto", "cor": "Loiro mel"},
        files=arquivo_de_foto(),
    ).json()

    resposta = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": outro["id"],
            "descricao": "Corte",
            "dataServico": date.today().isoformat(),
            "simulacaoId": simulacao["id"],
        },
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "simulacao_de_outro_cliente"


def test_atendimento_de_outra_conta_responde_404(cliente_http: TestClient, conta):
    cabecalhos_a, _ = conta()
    cabecalhos_b, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos_a)
    atendimento = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos_a,
        json={
            "clienteId": cliente["id"],
            "descricao": "Corte",
            "dataServico": date.today().isoformat(),
        },
    ).json()

    assert cliente_http.get(
        f"/api/v1/atendimentos/{atendimento['id']}", headers=cabecalhos_b
    ).status_code == 404
    assert cliente_http.patch(
        f"/api/v1/atendimentos/{atendimento['id']}", headers=cabecalhos_b, json={"descricao": "Corte novo"}
    ).status_code == 404


def test_atendimento_pode_ser_corrigido(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    atendimento = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "descricao": "Corte",
            "dataServico": date.today().isoformat(),
        },
    ).json()
    corrigido = cliente_http.patch(
        f"/api/v1/atendimentos/{atendimento['id']}",
        headers=cabecalhos,
        json={"observacoes": "Cliente pediu dois dedos a menos."},
    )
    assert corrigido.status_code == 200
    assert corrigido.json()["observacoes"].startswith("Cliente pediu")


# --- Agenda ---------------------------------------------------------------


def test_criar_agendamento_nasce_pendente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    resposta = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "dataHora": amanha(),
            "servico": "Coloração",
            "duracaoMin": 120,
            "lembrete": True,
        },
    )
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "pendente"
    assert resposta.json()["duracaoMin"] == 120


def test_duracao_fora_da_faixa(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    for duracao in (5, 600):
        resposta = cliente_http.post(
            "/api/v1/agendamentos",
            headers=cabecalhos,
            json={
                "clienteId": cliente["id"],
                "dataHora": amanha(),
                "servico": "Corte",
                "duracaoMin": duracao,
            },
        )
        assert resposta.status_code == 422


def test_agendamento_para_cliente_de_outra_conta(cliente_http: TestClient, conta):
    cabecalhos_a, _ = conta()
    cabecalhos_b, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos_a)
    resposta = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos_b,
        json={"clienteId": cliente["id"], "dataHora": amanha(), "servico": "Corte"},
    )
    assert resposta.status_code == 404


def test_transicoes_de_status(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    agendamento = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={"clienteId": cliente["id"], "dataHora": amanha(), "servico": "Corte"},
    ).json()
    caminho = f"/api/v1/agendamentos/{agendamento['id']}/status"

    # pendente → confirmado → concluido, pela rota genérica de status.
    assert cliente_http.patch(caminho, headers=cabecalhos, json={"status": "confirmado"}).json()[
        "status"
    ] == "confirmado"
    assert cliente_http.patch(caminho, headers=cabecalhos, json={"status": "concluido"}).json()[
        "status"
    ] == "concluido"

    # concluido é final: não volta a cancelado nem a confirmado.
    for destino in ("cancelado", "confirmado", "pendente"):
        resposta = cliente_http.patch(caminho, headers=cabecalhos, json={"status": destino})
        assert resposta.status_code == 422, f"concluído virou {destino}"


def test_pendente_pode_ser_concluido_sem_confirmar(cliente_http: TestClient, conta):
    """Regra revista: o cliente que chega sem ter sido confirmado continua atendido.

    Antes, pendente → concluído era recusado, e o profissional teria de confirmar um
    compromisso que já estava acontecendo só para poder registrar o serviço.
    """
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    agendamento = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={"clienteId": cliente["id"], "dataHora": amanha(), "servico": "Corte"},
    ).json()
    caminho = f"/api/v1/agendamentos/{agendamento['id']}/status"
    resposta = cliente_http.patch(caminho, headers=cabecalhos, json={"status": "concluido"})
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "concluido"


def test_agendamento_finalizado_nao_e_editado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    agendamento = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={"clienteId": cliente["id"], "dataHora": amanha(), "servico": "Corte"},
    ).json()
    cliente_http.patch(
        f"/api/v1/agendamentos/{agendamento['id']}/status",
        headers=cabecalhos,
        json={"status": "cancelado"},
    )
    resposta = cliente_http.patch(
        f"/api/v1/agendamentos/{agendamento['id']}",
        headers=cabecalhos,
        json={"servico": "Outro serviço"},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "agendamento_finalizado"


def test_agenda_ordenada_e_filtrada_por_cliente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    um = novo_cliente(cliente_http, cabecalhos, "Marina Alves")
    outro = novo_cliente(cliente_http, cabecalhos, "Bruno Tavares")
    for cliente_id, hora in ((outro["id"], 18), (um["id"], 9)):
        cliente_http.post(
            "/api/v1/agendamentos",
            headers=cabecalhos,
            json={"clienteId": cliente_id, "dataHora": amanha(hora), "servico": "Corte"},
        )

    todos = cliente_http.get("/api/v1/agendamentos", headers=cabecalhos).json()
    assert [a["clienteId"] for a in todos] == [um["id"], outro["id"]]

    so_um = cliente_http.get(
        "/api/v1/agendamentos", headers=cabecalhos, params={"clienteId": um["id"]}
    ).json()
    assert len(so_um) == 1


def test_excluir_agendamento(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    agendamento = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={"clienteId": cliente["id"], "dataHora": amanha(), "servico": "Corte"},
    ).json()
    assert cliente_http.delete(
        f"/api/v1/agendamentos/{agendamento['id']}", headers=cabecalhos
    ).status_code == 204
    assert cliente_http.get("/api/v1/agendamentos", headers=cabecalhos).json() == []


def test_servico_fora_do_catalogo_e_aceito_e_preservado(cliente_http: TestClient, conta):
    """A opção "Outro" do aplicativo grava a descrição digitada no próprio campo.

    O servidor nunca validou `servico` contra uma lista — é texto livre, com tamanho
    mínimo e máximo. Este teste fixa esse contrato: sem ele, alguém poderia transformar o
    campo em enumeração e quebrar silenciosamente a opção "Outro" do aplicativo.
    """
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)

    resposta = cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "dataHora": amanha(),
            "servico": "Penteado para festa de formatura",
            "duracaoMin": 90,
            "lembrete": False,
        },
    )
    assert resposta.status_code == 201, resposta.text
    criado = resposta.json()
    assert criado["servico"] == "Penteado para festa de formatura"

    # Persistido: a releitura traz o mesmo texto, sem normalização nem truncamento.
    lido = cliente_http.get(f"/api/v1/agendamentos/{criado['id']}", headers=cabecalhos).json()
    assert lido["servico"] == "Penteado para festa de formatura"

    # E continua editável pelo mesmo caminho.
    alterado = cliente_http.patch(
        f"/api/v1/agendamentos/{criado['id']}",
        headers=cabecalhos,
        json={"servico": "Tratamento capilar"},
    ).json()
    assert alterado["servico"] == "Tratamento capilar"


def test_servico_vazio_ou_curto_demais_e_recusado(cliente_http: TestClient, conta):
    """Texto livre não quer dizer qualquer coisa: a descrição do "Outro" precisa existir."""
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)

    for servico in ("", " ", "a"):
        resposta = cliente_http.post(
            "/api/v1/agendamentos",
            headers=cabecalhos,
            json={
                "clienteId": cliente["id"],
                "dataHora": amanha(),
                "servico": servico,
                "duracaoMin": 60,
                "lembrete": False,
            },
        )
        assert resposta.status_code == 422, f"serviço {servico!r} foi aceito"
