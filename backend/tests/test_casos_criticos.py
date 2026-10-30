"""Os sete casos críticos exigidos pela seção 33 da especificação.

Cada teste prova uma afirmação que o TCC faz sobre o sistema. Estão juntos, com os nomes
na mesma ordem do enunciado, para servirem de evidência direta.
"""

from __future__ import annotations

import time
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import engine
from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def novo_cliente(cliente_http, cabecalhos, nome="Marina Alves", nascimento=None):
    corpo = {"nome": nome, "telefone": "(55) 99000-0000"}
    if nascimento:
        corpo["dataNascimento"] = nascimento
    return cliente_http.post("/api/v1/clientes", headers=cabecalhos, json=corpo).json()


def tentar_simular(cliente_http, cabecalhos, cliente_id):
    return cliente_http.post(
        "/api/v1/simulacoes",
        headers=cabecalhos,
        data={"clienteId": cliente_id, "corte": "Bob curto", "cor": "Loiro mel"},
        files=arquivo_de_foto(),
    )


def aguardar(cliente_http, cabecalhos, simulacao_id):
    for _ in range(60):
        estado = cliente_http.get(f"/api/v1/simulacoes/{simulacao_id}", headers=cabecalhos).json()
        if estado["status"] != "processando":
            return estado
        time.sleep(0.2)
    raise AssertionError("simulação presa em processando")


# 1 ------------------------------------------------------------------------
def test_1_cliente_sem_consentimento_nao_pode_gerar_simulacao(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)

    resposta = tentar_simular(cliente_http, cabecalhos, cliente["id"])
    assert resposta.status_code == 403
    erro = resposta.json()["erro"]
    assert erro["codigo"] == "consentimento_invalido"
    assert erro["detalhes"][0]["motivo"] == "pendente"
    # Nada foi criado, nem simulação em falha.
    assert cliente_http.get(
        f"/api/v1/clientes/{cliente['id']}/simulacoes", headers=cabecalhos
    ).json() == []


# 2 ------------------------------------------------------------------------
def test_2_consentimento_revogado_nao_pode_gerar_simulacao(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    caminho = f"/api/v1/clientes/{cliente['id']}/consentimentos"
    cliente_http.post(caminho, headers=cabecalhos, json=ACEITE)

    liberada = tentar_simular(cliente_http, cabecalhos, cliente["id"])
    assert liberada.status_code == 202  # com aceite, passa

    cliente_http.post(
        caminho, headers=cabecalhos, json={**ACEITE, "decisao": "revogado"}
    )
    bloqueada = tentar_simular(cliente_http, cabecalhos, cliente["id"])
    assert bloqueada.status_code == 403
    assert bloqueada.json()["erro"]["detalhes"][0]["motivo"] == "revogado"


# 3 ------------------------------------------------------------------------
def test_3_consentimento_antigo_exige_revalidacao(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
    )

    # Publica uma versão nova do termo: o aceite anterior continua existindo, mas não vale.
    with engine.begin() as conexao:
        conexao.execute(text("UPDATE termos SET vigente = false WHERE tipo = 'cliente'"))
        conexao.execute(
            text(
                """
                INSERT INTO termos (id, tipo, versao, vigente_desde, vigente, titulo, resumo, secoes)
                VALUES (gen_random_uuid(), 'cliente', '2.0', current_date, true,
                        'Termo 2.0', 'resumo', '[]'::jsonb)
                """
            )
        )
    try:
        resposta = tentar_simular(cliente_http, cabecalhos, cliente["id"])
        assert resposta.status_code == 403
        assert resposta.json()["erro"]["detalhes"][0]["motivo"] == "revalidar"

        # Reapresentado o texto novo, a captura volta a ser permitida.
        cliente_http.post(
            f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
        )
        assert tentar_simular(cliente_http, cabecalhos, cliente["id"]).status_code == 202
    finally:
        with engine.begin() as conexao:
            # TRUNCATE porque DELETE em `consentimentos` é barrado pelo gatilho — e é
            # exatamente esse o comportamento desejado (ver test_imutabilidade).
            conexao.execute(text("TRUNCATE consentimentos CASCADE"))
            conexao.execute(text("DELETE FROM termos WHERE versao = '2.0'"))
            conexao.execute(
                text("UPDATE termos SET vigente = true WHERE tipo = 'cliente' AND versao = '1.0'")
            )


# 4 ------------------------------------------------------------------------
def test_4_usuario_a_nao_acessa_dados_do_usuario_b(cliente_http: TestClient, conta):
    cabecalhos_a, _ = conta()
    cabecalhos_b, _ = conta()
    cliente_a = novo_cliente(cliente_http, cabecalhos_a)
    cliente_http.post(
        f"/api/v1/clientes/{cliente_a['id']}/consentimentos", headers=cabecalhos_a, json=ACEITE
    )
    simulacao = tentar_simular(cliente_http, cabecalhos_a, cliente_a["id"]).json()

    # B troca o id na URL: em nenhum caminho obtém dado de A.
    assert cliente_http.get(f"/api/v1/clientes/{cliente_a['id']}", headers=cabecalhos_b).status_code == 404
    assert cliente_http.get(f"/api/v1/simulacoes/{simulacao['id']}", headers=cabecalhos_b).status_code == 404
    assert cliente_http.post(
        f"/api/v1/simulacoes/{simulacao['id']}/preferida", headers=cabecalhos_b
    ).status_code == 404
    assert cliente_http.post(
        f"/api/v1/clientes/{cliente_a['id']}/consentimentos", headers=cabecalhos_b, json=ACEITE
    ).status_code == 404
    assert tentar_simular(cliente_http, cabecalhos_b, cliente_a["id"]).status_code == 404
    assert cliente_http.get("/api/v1/clientes", headers=cabecalhos_b).json() == []

    # E a imagem de A não abre com a assinatura pedida por B.
    entrada = simulacao["imgEntradaUri"].replace("http://testserver", "")
    assert cliente_http.get(entrada).status_code == 200  # a assinatura legítima funciona
    assert cliente_http.get(entrada.split("?")[0] + "?t=0.falsa").status_code == 404


# 5 ------------------------------------------------------------------------
def test_5_menor_sem_responsavel_nao_registra_consentimento(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    nascimento = date(date.today().year - 15, 6, 1).isoformat()
    cliente = novo_cliente(cliente_http, cabecalhos, "Sofia Ramires", nascimento)

    resposta = cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos",
        headers=cabecalhos,
        json={**ACEITE, "confirmadoPor": "Sofia Ramires"},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "responsavel_obrigatorio"
    # Sem registro, a câmera continua bloqueada.
    assert tentar_simular(cliente_http, cabecalhos, cliente["id"]).status_code == 403


# 6 ------------------------------------------------------------------------
def test_6_revogacao_cria_novo_registro(cliente_http: TestClient, conta, sessao):
    from app.models import Consentimento

    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    caminho = f"/api/v1/clientes/{cliente['id']}/consentimentos"

    aceite = cliente_http.post(caminho, headers=cabecalhos, json=ACEITE).json()["registro"]
    revogacao = cliente_http.post(
        caminho, headers=cabecalhos, json={**ACEITE, "decisao": "revogado"}
    ).json()["registro"]

    assert revogacao["id"] != aceite["id"]
    historico = cliente_http.get(caminho, headers=cabecalhos).json()
    assert [r["decisao"] for r in historico] == ["revogado", "aceito"]

    # O registro antigo continua no banco, intacto.
    antigo = sessao.get(Consentimento, aceite["id"])
    assert antigo is not None
    assert antigo.decisao.value == "aceito"


# 7 ------------------------------------------------------------------------
def test_7_exclusao_de_imagens_nao_apaga_o_historico(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    cliente_http.post(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE
    )
    simulacao = aguardar(
        cliente_http, cabecalhos, tentar_simular(cliente_http, cabecalhos, cliente["id"]).json()["id"]
    )
    atendimento = cliente_http.post(
        "/api/v1/atendimentos",
        headers=cabecalhos,
        json={
            "clienteId": cliente["id"],
            "descricao": "Coloração acobreada",
            "dataServico": date.today().isoformat(),
            "simulacaoId": simulacao["id"],
        },
    ).json()
    assert atendimento["simulacaoId"] == simulacao["id"]

    apagada = cliente_http.delete(
        f"/api/v1/clientes/{cliente['id']}/simulacoes", headers=cabecalhos
    )
    assert apagada.status_code == 204

    assert cliente_http.get(
        f"/api/v1/clientes/{cliente['id']}/simulacoes", headers=cabecalhos
    ).json() == []

    historico = cliente_http.get(
        f"/api/v1/clientes/{cliente['id']}/historico", headers=cabecalhos
    ).json()
    assert len(historico) == 1
    assert historico[0]["descricao"] == "Coloração acobreada"
    assert historico[0]["simulacaoId"] is None  # perdeu só o vínculo

    # O histórico de consentimentos também permanece: é registro de decisão, não imagem.
    assert len(
        cliente_http.get(
            f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos
        ).json()
    ) == 1

    # E o arquivo saiu do storage.
    assert cliente_http.get(
        simulacao["imgSaidaUri"].replace("http://testserver", "")
    ).status_code == 404


@pytest.mark.parametrize("motivo", ["recusado", "revogado"])
def test_bloqueio_vale_para_recusa_e_revogacao(cliente_http: TestClient, conta, motivo):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    caminho = f"/api/v1/clientes/{cliente['id']}/consentimentos"
    if motivo == "revogado":
        cliente_http.post(caminho, headers=cabecalhos, json=ACEITE)
    cliente_http.post(caminho, headers=cabecalhos, json={**ACEITE, "decisao": motivo})

    resposta = tentar_simular(cliente_http, cabecalhos, cliente["id"])
    assert resposta.status_code == 403
    assert resposta.json()["erro"]["detalhes"][0]["motivo"] == motivo
