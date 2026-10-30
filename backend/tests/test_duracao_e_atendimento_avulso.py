"""Duração opcional do agendamento e atendimento registrado sem agendamento.

- Sem duração informada, o agendamento é salvo sem duração: nada de 60 minutos presumidos.
- O conflito de horário continua valendo: sem duração, o compromisso ocupa o horário de
  início.
- O atendimento registrado pelo perfil do cliente (o cliente chegou sem marcar) entra no
  histórico daquele cliente com dia, hora, duração e serviço informados, sem criar nem
  concluir agendamento nenhum.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from tests.test_agenda_fluxo import agendar, cliente, daqui

BRASILIA = timezone(timedelta(hours=-3))


def amanha_as(hora: int, minuto: int = 0) -> str:
    dia = (datetime.now(BRASILIA) + timedelta(days=1)).date()
    return datetime(dia.year, dia.month, dia.day, hora, minuto, tzinfo=BRASILIA).isoformat()


# --- duração opcional --------------------------------------------------------------


def test_cria_agendamento_sem_duracao(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    corpo = {
        "clienteId": c["id"],
        "dataHora": daqui(),
        "servico": "Corte",
        "observacoes": "",
        "lembrete": False,
    }
    resposta = cliente_http.post("/api/v1/agendamentos", headers=cabecalhos, json=corpo)
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["duracaoMin"] is None, "nenhuma duração pode ser presumida"

    # Enviar null explicitamente dá o mesmo resultado.
    corpo["dataHora"] = daqui(48)
    explicito = cliente_http.post(
        "/api/v1/agendamentos", headers=cabecalhos, json={**corpo, "duracaoMin": None}
    )
    assert explicito.status_code == 201 and explicito.json()["duracaoMin"] is None

    lista = cliente_http.get("/api/v1/agendamentos", headers=cabecalhos).json()
    assert [a["duracaoMin"] for a in lista] == [None, None]


def test_cria_agendamento_com_duracao_manual(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    resposta = agendar(cliente_http, cabecalhos, c["id"], duracao=90)
    assert resposta.status_code == 201 and resposta.json()["duracaoMin"] == 90


@pytest.mark.parametrize("duracao", [0, 14, 481, -30])
def test_duracao_fora_da_faixa_e_recusada(cliente_http: TestClient, conta, duracao):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    assert agendar(cliente_http, cabecalhos, c["id"], duracao=duracao).status_code == 422


def test_editar_sem_mencionar_duracao_mantem_e_null_apaga(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"], duracao=45).json()
    url = f"/api/v1/agendamentos/{a['id']}"

    mantida = cliente_http.patch(url, headers=cabecalhos, json={"observacoes": "nova nota"})
    assert mantida.json()["duracaoMin"] == 45

    apagada = cliente_http.patch(url, headers=cabecalhos, json={"duracaoMin": None})
    assert apagada.status_code == 200 and apagada.json()["duracaoMin"] is None

    informada = cliente_http.patch(url, headers=cabecalhos, json={"duracaoMin": 120})
    assert informada.json()["duracaoMin"] == 120


def test_conflito_sem_duracao_ocupa_o_horario_de_inicio(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    assert agendar(cliente_http, cabecalhos, c["id"], quando=amanha_as(14), duracao=None).status_code == 201

    # Mesmo horário de início: conflito.
    mesmo = agendar(cliente_http, cabecalhos, c["id"], quando=amanha_as(14), duracao=None)
    assert mesmo.status_code == 422 and mesmo.json()["erro"]["codigo"] == "horario_ocupado"
    # Um compromisso de 13h30 com 1 hora passa por cima das 14h: conflito.
    por_cima = agendar(cliente_http, cabecalhos, c["id"], quando=amanha_as(13, 30), duracao=60)
    assert por_cima.status_code == 422
    # Terminar exatamente às 14h não conflita.
    antes = agendar(cliente_http, cabecalhos, c["id"], quando=amanha_as(13), duracao=60)
    assert antes.status_code == 201
    # Logo depois do início, sem duração: livre (nada foi presumido sobre o término).
    depois = agendar(cliente_http, cabecalhos, c["id"], quando=amanha_as(14, 15), duracao=None)
    assert depois.status_code == 201


def test_sem_duracao_dentro_de_um_compromisso_em_andamento_conflita(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    assert agendar(cliente_http, cabecalhos, c["id"], quando=amanha_as(10), duracao=120).status_code == 201
    dentro = agendar(cliente_http, cabecalhos, c["id"], quando=amanha_as(11), duracao=None)
    assert dentro.status_code == 422
    no_fim = agendar(cliente_http, cabecalhos, c["id"], quando=amanha_as(12), duracao=None)
    assert no_fim.status_code == 201


def test_conclusao_guarda_a_duracao_informada_e_nao_presume(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    com = agendar(cliente_http, cabecalhos, c["id"], quando=daqui(1), duracao=60).json()
    sem = agendar(cliente_http, cabecalhos, c["id"], quando=daqui(5), duracao=60).json()

    feito = cliente_http.post(
        f"/api/v1/agendamentos/{com['id']}/concluir",
        headers=cabecalhos,
        json={"realizadoEm": datetime.now(UTC).isoformat(), "duracaoMin": 75},
    ).json()
    assert feito["atendimento"]["duracaoMin"] == 75
    # A duração prevista do agendamento continua a original.
    assert feito["agendamento"]["duracaoMin"] == 60

    sem_duracao = cliente_http.post(
        f"/api/v1/agendamentos/{sem['id']}/concluir", headers=cabecalhos, json={}
    ).json()
    assert sem_duracao["atendimento"]["duracaoMin"] is None


def test_conclusao_guarda_o_servico_realizado_sem_tocar_no_previsto(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"], quando=daqui(1), servico="Penteado para festa").json()
    feito = cliente_http.post(
        f"/api/v1/agendamentos/{a['id']}/concluir",
        headers=cabecalhos,
        json={"descricao": "Escova", "realizadoEm": datetime.now(UTC).isoformat()},
    ).json()
    assert feito["atendimento"]["descricao"] == "Escova"
    assert feito["agendamento"]["servico"] == "Penteado para festa"


# --- atendimento avulso ------------------------------------------------------------


def registrar(cliente_http, cabecalhos, cliente_id, **extra):
    corpo = {
        "clienteId": cliente_id,
        "descricao": "Corte",
        "realizadoEm": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
        "duracaoMin": None,
        "observacoes": "Chegou sem marcar",
        "simulacaoId": None,
    }
    corpo.update(extra)
    return cliente_http.post("/api/v1/atendimentos", headers=cabecalhos, json=corpo)


def test_atendimento_avulso_entra_no_historico_do_cliente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    quando = datetime(2026, 10, 20, 16, 45, tzinfo=BRASILIA)
    resposta = registrar(
        cliente_http,
        cabecalhos,
        c["id"],
        descricao="Penteado para festa",
        realizadoEm=quando.isoformat(),
        duracaoMin=90,
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["agendamentoId"] is None, "avulso não tem agendamento de origem"
    assert corpo["dataServico"] == "2026-10-20"
    assert datetime.fromisoformat(corpo["realizadoEm"]) == quando
    assert corpo["duracaoMin"] == 90
    assert corpo["descricao"] == "Penteado para festa"

    historico = cliente_http.get(
        "/api/v1/atendimentos", headers=cabecalhos, params={"clienteId": c["id"]}
    ).json()
    assert [h["id"] for h in historico] == [corpo["id"]]


def test_atendimento_avulso_nao_cria_nem_conclui_agendamento(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    pendente = agendar(cliente_http, cabecalhos, c["id"]).json()
    assert registrar(cliente_http, cabecalhos, c["id"]).status_code == 201

    agenda = cliente_http.get("/api/v1/agendamentos", headers=cabecalhos).json()
    assert len(agenda) == 1, "nenhum agendamento fictício pode ser criado"
    assert agenda[0]["id"] == pendente["id"] and agenda[0]["status"] == "pendente"


def test_atendimento_avulso_vai_para_o_cliente_certo(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    ana = cliente(cliente_http, cabecalhos, "Ana")
    bia = cliente(cliente_http, cabecalhos, "Bia")
    registrar(cliente_http, cabecalhos, ana["id"])
    da_bia = cliente_http.get(
        "/api/v1/atendimentos", headers=cabecalhos, params={"clienteId": bia["id"]}
    ).json()
    assert da_bia == []


def test_atendimento_avulso_no_futuro_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    resposta = registrar(cliente_http, cabecalhos, c["id"], realizadoEm=daqui(3))
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "atendimento_no_futuro"
    assert cliente_http.get("/api/v1/atendimentos", headers=cabecalhos).json() == []


def test_atendimento_avulso_perto_da_meia_noite_fica_no_dia_do_salao(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    # 23h30 de Brasília é 02h30 do dia seguinte em Greenwich.
    quando = datetime(2026, 10, 21, 23, 30, tzinfo=BRASILIA)
    corpo = registrar(cliente_http, cabecalhos, c["id"], realizadoEm=quando.isoformat()).json()
    assert corpo["dataServico"] == "2026-10-21"


def test_atendimento_avulso_exige_saber_quando(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    resposta = registrar(cliente_http, cabecalhos, c["id"], realizadoEm=None)
    assert resposta.status_code == 422


def test_formato_antigo_so_com_o_dia_continua_aceito(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    resposta = registrar(cliente_http, cabecalhos, c["id"], realizadoEm=None, dataServico="2026-10-01")
    assert resposta.status_code == 201
    assert resposta.json()["realizadoEm"] is None, "a hora não é inventada"


def test_atendimento_avulso_de_cliente_de_outra_conta_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    outra, _ = conta()
    alheio = cliente(cliente_http, outra)
    assert registrar(cliente_http, cabecalhos, alheio["id"]).status_code == 404


@pytest.mark.parametrize("duracao", [10, 500])
def test_duracao_do_atendimento_fora_da_faixa(cliente_http: TestClient, conta, duracao):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    assert registrar(cliente_http, cabecalhos, c["id"], duracaoMin=duracao).status_code == 422


# --- migration ---------------------------------------------------------------------


def test_volta_da_migration_recusa_inventar_duracao(cliente_http: TestClient, conta):
    from alembic import command
    from alembic.config import Config

    from tests.conftest import RAIZ

    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    agendar(cliente_http, cabecalhos, c["id"], duracao=None)
    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    with pytest.raises(RuntimeError, match="sem duração"):
        command.downgrade(configuracao, "e5a9c3f17b20")
    lista = cliente_http.get("/api/v1/agendamentos", headers=cabecalhos).json()
    assert lista[0]["duracaoMin"] is None
