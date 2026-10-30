"""Fluxo completo da agenda: datas passadas, conflitos, confirmação, cancelamento, conclusão.

Cada teste corresponde a um cenário dos itens 11.1 e 11.2 da especificação desta etapa. Todos
batem direto na API, sem passar pela tela: é exatamente a forma de "burlar a restrição
enviando uma requisição ao backend", e por isso é a forma certa de testar a restrição.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.session import engine
from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}

BRASILIA = timezone(timedelta(hours=-3))


def daqui(horas: float = 24, minutos: float = 0) -> str:
    return (datetime.now(UTC) + timedelta(hours=horas, minutes=minutos)).isoformat()


def cliente(cliente_http: TestClient, cabecalhos, nome: str = "Marina Alves") -> dict:
    return cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": nome, "telefone": "1"}
    ).json()


def agendar(cliente_http, cabecalhos, cliente_id, quando=None, duracao=60, servico="Corte"):
    return cliente_http.post(
        "/api/v1/agendamentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente_id,
            "dataHora": quando or daqui(),
            "servico": servico,
            "duracaoMin": duracao,
            "observacoes": "Trazer foto de referência",
            "lembrete": False,
        },
    )


# --- 11.1 (1-3, 12): datas passadas ------------------------------------------


def test_cria_agendamento_futuro(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    resposta = agendar(cliente_http, cabecalhos, c["id"])
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "pendente"


@pytest.mark.parametrize(
    "quando",
    [
        pytest.param(lambda: (datetime.now(UTC) - timedelta(days=1)).isoformat(), id="ontem"),
        pytest.param(lambda: (datetime.now(UTC) - timedelta(days=400)).isoformat(), id="ano-passado"),
        pytest.param(lambda: (datetime.now(UTC) - timedelta(hours=2)).isoformat(), id="duas-horas-atras"),
    ],
)
def test_recusa_data_passada_vinda_direto_da_api(cliente_http: TestClient, conta, quando):
    """Não é o seletor de data que impede: é o servidor, para qualquer requisição."""
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    resposta = agendar(cliente_http, cabecalhos, c["id"], quando=quando())
    assert resposta.status_code == 422, resposta.text
    erro = resposta.json()["erro"]
    assert erro["codigo"] == "data_passada"
    assert "já passou" in erro["mensagem"]


def test_dia_22_recusado_quando_hoje_e_23(cliente_http: TestClient, conta):
    """O exemplo literal do enunciado, com o relógio de referência deslocado para lá."""
    from app.services import agendamentos as servico

    referencia = datetime(2026, 10, 23, 15, 0, tzinfo=BRASILIA)
    original = servico._agora
    servico._agora = lambda: referencia.astimezone(UTC)
    try:
        cabecalhos, _ = conta()
        c = cliente(cliente_http, cabecalhos)
        dia_22 = datetime(2026, 10, 22, 15, 0, tzinfo=BRASILIA).isoformat()
        dia_24 = datetime(2026, 10, 24, 9, 0, tzinfo=BRASILIA).isoformat()
        assert agendar(cliente_http, cabecalhos, c["id"], quando=dia_22).status_code == 422
        assert agendar(cliente_http, cabecalhos, c["id"], quando=dia_24).status_code == 201
    finally:
        servico._agora = original


def test_fuso_nao_confunde_utc_com_horario_local(cliente_http: TestClient, conta):
    """23h30 de Brasília em 23/10 é 02h30 UTC de 24/10: o mesmo instante.

    Com o relógio parado às 23h00 de Brasília, 23h30 de Brasília (escrito em UTC, já no
    "dia seguinte") é futuro e passa; 22h30 de Brasília é passado e é recusado. Se o
    servidor comparasse datas sem fuso, erraria um dos dois.
    """
    from app.services import agendamentos as servico

    referencia = datetime(2026, 10, 23, 23, 0, tzinfo=BRASILIA)
    original = servico._agora
    servico._agora = lambda: referencia.astimezone(UTC)
    try:
        cabecalhos, _ = conta()
        c = cliente(cliente_http, cabecalhos)
        futuro_escrito_em_utc = datetime(2026, 10, 24, 2, 30, tzinfo=UTC).isoformat()
        passado_escrito_em_utc = datetime(2026, 10, 24, 1, 30, tzinfo=UTC).isoformat()
        assert agendar(cliente_http, cabecalhos, c["id"], quando=futuro_escrito_em_utc).status_code == 201
        assert agendar(cliente_http, cabecalhos, c["id"], quando=passado_escrito_em_utc).status_code == 422
    finally:
        servico._agora = original


def test_horario_sem_fuso_e_recusado(cliente_http: TestClient, conta):
    """'2026-10-24T10:00' sem fuso é ambíguo em três horas. A API exige o fuso."""
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    sem_fuso = (datetime.now() + timedelta(days=2)).replace(microsecond=0).isoformat()
    assert "+" not in sem_fuso and "Z" not in sem_fuso
    resposta = agendar(cliente_http, cabecalhos, c["id"], quando=sem_fuso)
    assert resposta.status_code == 422


# --- 11.1 (4-5): edição ---------------------------------------------------------


def test_edita_agendamento_valido(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"]).json()
    novo_horario = daqui(horas=48)
    resposta = cliente_http.patch(
        f"/api/v1/agendamentos/{a['id']}",
        headers=cabecalhos,
        json={"dataHora": novo_horario, "servico": "Coloração", "duracaoMin": 120, "observacoes": "Tom mel"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["servico"] == "Coloração" and corpo["duracaoMin"] == 120
    assert corpo["observacoes"] == "Tom mel"

    # Persistido: a releitura traz o mesmo.
    lido = cliente_http.get(f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos).json()
    assert lido["servico"] == "Coloração"
    assert datetime.fromisoformat(lido["dataHora"]) == datetime.fromisoformat(novo_horario)


def test_recusa_editar_para_data_passada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"]).json()
    resposta = cliente_http.patch(
        f"/api/v1/agendamentos/{a['id']}",
        headers=cabecalhos,
        json={"dataHora": (datetime.now(UTC) - timedelta(days=1)).isoformat()},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "data_passada"
    # E nada mudou.
    lido = cliente_http.get(f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos).json()
    assert lido["dataHora"] == a["dataHora"]


def test_editar_so_a_observacao_de_compromisso_ja_passado_e_permitido(cliente_http: TestClient, conta):
    """A data só é conferida quando muda. Um compromisso de hoje cedo continua anotável."""
    from app.services import agendamentos as servico

    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"], quando=daqui(horas=1)).json()

    original = servico._agora
    servico._agora = lambda: datetime.now(UTC) + timedelta(hours=3)  # o compromisso "passou"
    try:
        resposta = cliente_http.patch(
            f"/api/v1/agendamentos/{a['id']}",
            headers=cabecalhos,
            json={"observacoes": "Cliente atrasou 20 minutos"},
        )
        assert resposta.status_code == 200, resposta.text
    finally:
        servico._agora = original


def test_trocar_cliente_exige_cliente_da_propria_conta(cliente_http: TestClient, conta):
    cabecalhos_a, _ = conta()
    cabecalhos_b, _ = conta()
    c1 = cliente(cliente_http, cabecalhos_a, "Cliente Um")
    c2 = cliente(cliente_http, cabecalhos_a, "Cliente Dois")
    de_b = cliente(cliente_http, cabecalhos_b, "Cliente de B")
    a = agendar(cliente_http, cabecalhos_a, c1["id"]).json()

    alheio = cliente_http.patch(
        f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos_a, json={"clienteId": de_b["id"]}
    )
    assert alheio.status_code == 404, "aceitou cliente de outra conta"

    proprio = cliente_http.patch(
        f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos_a, json={"clienteId": c2["id"]}
    )
    assert proprio.status_code == 200
    assert proprio.json()["clienteId"] == c2["id"]


# --- conflito de horário --------------------------------------------------------


def test_recusa_horario_sobreposto(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    inicio = datetime.now(UTC) + timedelta(days=3)
    assert agendar(cliente_http, cabecalhos, c["id"], quando=inicio.isoformat(), duracao=60).status_code == 201

    # Começa no meio do primeiro.
    meio = agendar(cliente_http, cabecalhos, c["id"], quando=(inicio + timedelta(minutes=30)).isoformat())
    assert meio.status_code == 422
    assert meio.json()["erro"]["codigo"] == "horario_ocupado"

    # Começa exatamente quando o primeiro termina: não sobrepõe.
    encostado = agendar(cliente_http, cabecalhos, c["id"], quando=(inicio + timedelta(minutes=60)).isoformat())
    assert encostado.status_code == 201


def test_cancelado_libera_o_horario(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    quando = (datetime.now(UTC) + timedelta(days=4)).isoformat()
    a = agendar(cliente_http, cabecalhos, c["id"], quando=quando).json()
    cliente_http.post(f"/api/v1/agendamentos/{a['id']}/cancelar", headers=cabecalhos, json={})
    assert agendar(cliente_http, cabecalhos, c["id"], quando=quando).status_code == 201


def test_conflito_e_por_profissional(cliente_http: TestClient, conta):
    """O horário ocupado de uma conta não bloqueia outra."""
    cabecalhos_a, _ = conta()
    cabecalhos_b, _ = conta()
    quando = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    assert agendar(cliente_http, cabecalhos_a, cliente(cliente_http, cabecalhos_a)["id"], quando=quando).status_code == 201
    assert agendar(cliente_http, cabecalhos_b, cliente(cliente_http, cabecalhos_b)["id"], quando=quando).status_code == 201


def test_editar_nao_conflita_consigo_mesmo(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"], duracao=60).json()
    # Estender a própria duração não pode ser recusado por sobrepor... a si mesmo.
    resposta = cliente_http.patch(
        f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos, json={"duracaoMin": 90}
    )
    assert resposta.status_code == 200


# --- 11.1 (6-8): confirmar e cancelar ---------------------------------------------


def test_confirma_pendente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    a = agendar(cliente_http, cabecalhos, cliente(cliente_http, cabecalhos)["id"]).json()
    resposta = cliente_http.post(f"/api/v1/agendamentos/{a['id']}/confirmar", headers=cabecalhos)
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "confirmado"
    # Repetir é inofensivo.
    assert cliente_http.post(f"/api/v1/agendamentos/{a['id']}/confirmar", headers=cabecalhos).status_code == 200


@pytest.mark.parametrize("finalizacao", ["cancelar", "concluir"])
def test_nao_confirma_finalizado(cliente_http: TestClient, conta, finalizacao):
    cabecalhos, _ = conta()
    a = agendar(cliente_http, cabecalhos, cliente(cliente_http, cabecalhos)["id"]).json()
    cliente_http.post(f"/api/v1/agendamentos/{a['id']}/{finalizacao}", headers=cabecalhos, json={})
    resposta = cliente_http.post(f"/api/v1/agendamentos/{a['id']}/confirmar", headers=cabecalhos)
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "transicao_invalida"


def test_cancela_e_preserva_o_registro(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    a = agendar(cliente_http, cabecalhos, cliente(cliente_http, cabecalhos)["id"]).json()
    resposta = cliente_http.post(
        f"/api/v1/agendamentos/{a['id']}/cancelar",
        headers=cabecalhos,
        json={"motivo": "Cliente pediu para remarcar"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "cancelado"
    assert corpo["canceladoEm"] is not None
    assert corpo["motivoCancelamento"] == "Cliente pediu para remarcar"

    # Persistido, e o registro continua existindo: cancelar não é apagar.
    lido = cliente_http.get(f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos)
    assert lido.status_code == 200
    assert lido.json()["status"] == "cancelado"

    # Cancelado não é concluído, nem volta a ser editado.
    assert cliente_http.post(f"/api/v1/agendamentos/{a['id']}/concluir", headers=cabecalhos, json={}).status_code == 422
    assert cliente_http.patch(f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos, json={"servico": "Outro"}).status_code == 422


# --- 11.1 (9-10) e 11.2: conclusão e histórico ------------------------------------


def test_conclui_e_cria_o_atendimento_vinculado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"], servico="Coloração").json()

    resposta = cliente_http.post(
        f"/api/v1/agendamentos/{a['id']}/concluir",
        headers=cabecalhos,
        json={"observacoes": "Tom 7.43, 35 minutos de pausa"},
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["agendamento"]["status"] == "concluido"
    atendimento = corpo["atendimento"]
    assert atendimento["agendamentoId"] == a["id"]
    assert atendimento["clienteId"] == c["id"]
    assert atendimento["descricao"] == "Coloração", "o serviço previsto não foi preservado"
    assert atendimento["observacoes"] == "Tom 7.43, 35 minutos de pausa"
    assert atendimento["realizadoEm"] is not None
    assert corpo["agendamento"]["atendimentoId"] == atendimento["id"]

    # O horário marcado NÃO foi sobrescrito pelo horário real.
    lido = cliente_http.get(f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos).json()
    assert lido["dataHora"] == a["dataHora"]

    # E o atendimento aparece no histórico do cliente certo.
    historico = cliente_http.get(f"/api/v1/clientes/{c['id']}/historico", headers=cabecalhos).json()
    assert [h["id"] for h in historico] == [atendimento["id"]]


def test_conclusao_repetida_nao_duplica(cliente_http: TestClient, conta):
    """O botão apertado duas vezes, ou a requisição reenviada pela rede."""
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"]).json()
    rota = f"/api/v1/agendamentos/{a['id']}/concluir"

    primeiro = cliente_http.post(rota, headers=cabecalhos, json={}).json()["atendimento"]
    for _ in range(3):
        repetido = cliente_http.post(rota, headers=cabecalhos, json={})
        assert repetido.status_code == 200
        assert repetido.json()["atendimento"]["id"] == primeiro["id"]

    historico = cliente_http.get(f"/api/v1/clientes/{c['id']}/historico", headers=cabecalhos).json()
    assert len(historico) == 1, f"o atendimento foi duplicado: {len(historico)}"


def test_banco_recusa_dois_atendimentos_para_o_mesmo_agendamento(cliente_http: TestClient, conta):
    """A barreira final contra duplicidade é o índice único, não o código."""
    cabecalhos, usuario = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"]).json()
    cliente_http.post(f"/api/v1/agendamentos/{a['id']}/concluir", headers=cabecalhos, json={})

    with pytest.raises(IntegrityError), engine.begin() as conexao:
        conexao.execute(
            text(
                """
                INSERT INTO atendimentos
                    (id, cliente_id, usuario_id, agendamento_id, descricao, data_servico,
                     observacoes, criado_em)
                VALUES (gen_random_uuid(), :c, :u, :a, 'Duplicado', current_date, '', now())
                """
            ),
            {"c": c["id"], "u": usuario["id"], "a": a["id"]},
        )


def test_data_do_atendimento_e_a_do_salao_e_nao_a_de_greenwich(cliente_http: TestClient, conta):
    """22h30 de Brasília do dia 23 é 01h30 UTC do dia 24: o serviço foi no dia 23."""
    from app.services import agendamentos as servico

    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"]).json()

    concluido_em_utc = datetime(2026, 10, 24, 1, 30, tzinfo=UTC)
    original = servico._agora
    servico._agora = lambda: concluido_em_utc + timedelta(minutes=10)
    try:
        resposta = cliente_http.post(
            f"/api/v1/agendamentos/{a['id']}/concluir",
            headers=cabecalhos,
            json={"realizadoEm": concluido_em_utc.isoformat()},
        )
    finally:
        servico._agora = original
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["atendimento"]["dataServico"] == "2026-10-23"


def test_conclusao_no_futuro_e_recusada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    a = agendar(cliente_http, cabecalhos, cliente(cliente_http, cabecalhos)["id"]).json()
    resposta = cliente_http.post(
        f"/api/v1/agendamentos/{a['id']}/concluir",
        headers=cabecalhos,
        json={"realizadoEm": daqui(horas=5)},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "conclusao_no_futuro"
    # E nada foi gravado: a transação inteira desfeita.
    lido = cliente_http.get(f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos).json()
    assert lido["status"] == "pendente" and lido["atendimentoId"] is None


def test_concluir_com_simulacao_vinculada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    cliente_http.post(f"/api/v1/clientes/{c['id']}/consentimentos", headers=cabecalhos, json=ACEITE)
    simulacao = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": c["id"], "corte": "Bob curto", "cor": "Ruivo intenso", "observacoes": ""},
        files=arquivo_de_foto(),
    ).json()
    a = agendar(cliente_http, cabecalhos, c["id"]).json()

    resposta = cliente_http.post(
        f"/api/v1/agendamentos/{a['id']}/concluir",
        headers=cabecalhos,
        json={"simulacaoId": simulacao["id"]},
    )
    assert resposta.status_code == 200
    assert resposta.json()["atendimento"]["simulacaoId"] == simulacao["id"]


def test_nao_vincula_simulacao_de_outro_cliente(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    dona = cliente(cliente_http, cabecalhos, "Dona da simulação")
    outra = cliente(cliente_http, cabecalhos, "Outra cliente")
    cliente_http.post(f"/api/v1/clientes/{dona['id']}/consentimentos", headers=cabecalhos, json=ACEITE)
    simulacao = cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": dona["id"], "corte": "Bob curto", "cor": "Ruivo intenso", "observacoes": ""},
        files=arquivo_de_foto(),
    ).json()
    a = agendar(cliente_http, cabecalhos, outra["id"]).json()

    resposta = cliente_http.post(
        f"/api/v1/agendamentos/{a['id']}/concluir",
        headers=cabecalhos,
        json={"simulacaoId": simulacao["id"]},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "simulacao_de_outro_cliente"
    # Nada concluído por engano.
    assert cliente_http.get(f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos).json()["status"] == "pendente"


def test_historico_nao_mistura_clientes(cliente_http: TestClient, conta):
    """Mesmo dia, mesmo serviço: o vínculo é pelo identificador, não pela semelhança."""
    cabecalhos, _ = conta()
    c1 = cliente(cliente_http, cabecalhos, "Ana Souza")
    c2 = cliente(cliente_http, cabecalhos, "Ana Souza")  # homônima, de propósito
    a1 = agendar(cliente_http, cabecalhos, c1["id"], quando=daqui(horas=30)).json()
    a2 = agendar(cliente_http, cabecalhos, c2["id"], quando=daqui(horas=32)).json()
    cliente_http.post(f"/api/v1/agendamentos/{a1['id']}/concluir", headers=cabecalhos, json={})
    cliente_http.post(f"/api/v1/agendamentos/{a2['id']}/concluir", headers=cabecalhos, json={})

    h1 = cliente_http.get(f"/api/v1/clientes/{c1['id']}/historico", headers=cabecalhos).json()
    h2 = cliente_http.get(f"/api/v1/clientes/{c2['id']}/historico", headers=cabecalhos).json()
    assert [h["agendamentoId"] for h in h1] == [a1["id"]]
    assert [h["agendamentoId"] for h in h2] == [a2["id"]]


def test_concluido_antigo_sem_atendimento_nao_ganha_dado_inventado(cliente_http: TestClient, conta):
    """Registro anterior à vinculação: concluído, mas sem atendimento. Não se inventa um."""
    cabecalhos, _ = conta()
    a = agendar(cliente_http, cabecalhos, cliente(cliente_http, cabecalhos)["id"]).json()
    with engine.begin() as conexao:
        conexao.execute(text("UPDATE agendamentos SET status = 'concluido' WHERE id = :id"), {"id": a["id"]})

    resposta = cliente_http.post(f"/api/v1/agendamentos/{a['id']}/concluir", headers=cabecalhos, json={})
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "concluido_sem_atendimento"


def test_atendimento_antigo_sem_campos_novos_continua_legivel(cliente_http: TestClient, conta):
    """Atendimentos avulsos e antigos: sem agendamento e sem horário real. Exibem vazio."""
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    avulso = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={"clienteId": c["id"], "descricao": "Hidratação", "dataServico": "2026-09-10", "observacoes": ""},
    ).json()
    assert avulso["agendamentoId"] is None
    assert avulso["realizadoEm"] is None
    assert avulso["dataServico"] == "2026-09-10"


def test_concluido_nao_pode_ser_excluido(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    a = agendar(cliente_http, cabecalhos, cliente(cliente_http, cabecalhos)["id"]).json()
    cliente_http.post(f"/api/v1/agendamentos/{a['id']}/concluir", headers=cabecalhos, json={})
    resposta = cliente_http.delete(f"/api/v1/agendamentos/{a['id']}", headers=cabecalhos)
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "agendamento_concluido"


def test_rota_generica_de_status_nao_e_porta_lateral(cliente_http: TestClient, conta):
    """Concluir pela rota genérica também cria o atendimento. Sem isso, seria um atalho
    para um agendamento concluído sem registro no histórico."""
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    a = agendar(cliente_http, cabecalhos, c["id"]).json()
    cliente_http.patch(f"/api/v1/agendamentos/{a['id']}/status", headers=cabecalhos, json={"status": "concluido"})
    historico = cliente_http.get(f"/api/v1/clientes/{c['id']}/historico", headers=cabecalhos).json()
    assert len(historico) == 1 and historico[0]["agendamentoId"] == a["id"]


def test_agenda_reflete_as_mudancas(cliente_http: TestClient, conta):
    """A lista da agenda devolve o status atual de cada compromisso, sem recarga especial."""
    cabecalhos, _ = conta()
    c = cliente(cliente_http, cabecalhos)
    p = agendar(cliente_http, cabecalhos, c["id"], quando=daqui(horas=24)).json()
    x = agendar(cliente_http, cabecalhos, c["id"], quando=daqui(horas=27)).json()
    k = agendar(cliente_http, cabecalhos, c["id"], quando=daqui(horas=30)).json()
    cliente_http.post(f"/api/v1/agendamentos/{x['id']}/cancelar", headers=cabecalhos, json={})
    cliente_http.post(f"/api/v1/agendamentos/{k['id']}/concluir", headers=cabecalhos, json={})

    lista = {a["id"]: a for a in cliente_http.get("/api/v1/agendamentos", headers=cabecalhos).json()}
    assert lista[p["id"]]["status"] == "pendente"
    assert lista[x["id"]]["status"] == "cancelado"
    assert lista[k["id"]]["status"] == "concluido" and lista[k["id"]]["atendimentoId"]
