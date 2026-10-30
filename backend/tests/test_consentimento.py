"""RNF05 — registro, histórico, revogação, menor de idade e versionamento do termo."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import engine

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def novo_cliente(cliente_http: TestClient, cabecalhos, **extra) -> dict:
    corpo = {"nome": "Marina Alves", "telefone": "(55) 99123-4567", **extra}
    return cliente_http.post("/api/v1/clientes", headers=cabecalhos, json=corpo).json()


def registrar(cliente_http: TestClient, cabecalhos, cliente_id, **campos):
    return cliente_http.post(
        f"/api/v1/clientes/{cliente_id}/consentimentos",
        headers=cabecalhos,
        json={**ACEITE, **campos},
    )


def test_aceite_libera_e_grava_a_versao_vigente(cliente_http: TestClient, conta, versao_vigente):
    cabecalhos, usuario = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)

    resposta = registrar(cliente_http, cabecalhos, cliente["id"])
    assert resposta.status_code == 201
    resumo = resposta.json()
    assert resumo["status"] == "aceito"
    assert resumo["revalidar"] is False
    assert resumo["bloqueio"] is None
    assert resumo["registro"]["versaoTermo"] == versao_vigente()
    assert resumo["registro"]["usuarioId"] == usuario["id"]
    assert resumo["registro"]["faixaEtaria"] == "desconhecida"


def test_versao_enviada_pelo_aplicativo_e_ignorada(cliente_http: TestClient, conta, versao_vigente):
    """Um aplicativo desatualizado não consegue registrar aceite sobre texto antigo."""
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    resposta = registrar(cliente_http, cabecalhos, cliente["id"], versaoTermo="0.9")
    assert resposta.json()["registro"]["versaoTermo"] == versao_vigente()


def test_recusa_bloqueia_mas_mantem_o_cadastro(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    resumo = registrar(
        cliente_http, cabecalhos, cliente["id"], decisao="recusado", formaObtencao="lido_em_voz_alta"
    ).json()
    assert resumo["status"] == "recusado"
    assert resumo["bloqueio"]["motivo"] == "recusado"
    assert cliente_http.get(f"/api/v1/clientes/{cliente['id']}", headers=cabecalhos).status_code == 200


def test_revogacao_cria_novo_registro_e_preserva_o_historico(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    registrar(cliente_http, cabecalhos, cliente["id"])

    revogado = registrar(
        cliente_http,
        cabecalhos,
        cliente["id"],
        decisao="revogado",
        formaObtencao="lido_em_voz_alta",
        observacao="Pediu por telefone.",
    )
    assert revogado.status_code == 201
    assert revogado.json()["status"] == "revogado"

    historico = cliente_http.get(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos
    ).json()
    assert [r["decisao"] for r in historico] == ["revogado", "aceito"]


def test_revogar_sem_aceite_ativo_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    resposta = registrar(cliente_http, cabecalhos, cliente["id"], decisao="revogado")
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "sem_consentimento_ativo"


def test_cliente_pode_aceitar_depois_de_recusar(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    registrar(cliente_http, cabecalhos, cliente["id"], decisao="recusado")
    de_novo = registrar(cliente_http, cabecalhos, cliente["id"], decisao="aceito")
    assert de_novo.status_code == 201
    assert de_novo.json()["status"] == "aceito"
    assert de_novo.json()["bloqueio"] is None


def test_menor_sem_responsavel_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    nascimento = date(date.today().year - 16, 4, 12).isoformat()
    cliente = novo_cliente(
        cliente_http, cabecalhos, nome="Sofia Ramires", dataNascimento=nascimento
    )
    resposta = registrar(cliente_http, cabecalhos, cliente["id"], confirmadoPor="Sofia Ramires")
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "responsavel_obrigatorio"

    historico = cliente_http.get(
        f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos
    ).json()
    assert historico == []


def test_menor_com_responsavel_e_aceito(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    nascimento = date(date.today().year - 16, 4, 12).isoformat()
    cliente = novo_cliente(
        cliente_http, cabecalhos, nome="Sofia Ramires", dataNascimento=nascimento
    )
    resposta = registrar(
        cliente_http,
        cabecalhos,
        cliente["id"],
        confirmadoPor="Denise Ramires",
        responsavel={"nome": "Denise Ramires", "parentesco": "Mãe"},
    )
    assert resposta.status_code == 201
    registro = resposta.json()["registro"]
    assert registro["responsavel"] == {"nome": "Denise Ramires", "parentesco": "Mãe"}
    assert registro["faixaEtaria"] == "adolescente"


def test_responsavel_em_adulto_e_recusado(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos, dataNascimento="1990-05-05")
    resposta = registrar(
        cliente_http,
        cabecalhos,
        cliente["id"],
        responsavel={"nome": "Alguém", "parentesco": "Mãe"},
    )
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "responsavel_nao_aplicavel"


def test_aceite_em_versao_antiga_pede_revalidacao(cliente_http: TestClient, conta, versao_vigente):
    """Simula a publicação de uma versão nova depois do aceite."""
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    registrar(cliente_http, cabecalhos, cliente["id"])

    anterior = versao_vigente()
    # Número alto de propósito: tem de ser uma versão que o projeto nunca vai publicar,
    # senão o teste colide com a realidade a cada termo novo.
    futura = "99.0"
    with engine.begin() as conexao:
        conexao.execute(text("UPDATE termos SET vigente = false WHERE tipo = 'cliente'"))
        conexao.execute(
            text(
                """
                INSERT INTO termos (id, tipo, versao, vigente_desde, vigente, titulo, resumo, secoes)
                VALUES (gen_random_uuid(), 'cliente', :futura, current_date, true,
                        'Termo de teste', 'resumo', '[]'::jsonb)
                """
            ),
            {"futura": futura},
        )
    try:
        resumo = cliente_http.get(
            f"/api/v1/clientes/{cliente['id']}/consentimento", headers=cabecalhos
        ).json()
        assert resumo["status"] == "aceito"
        assert resumo["revalidar"] is True
        assert resumo["rotulo"] == "Aceito em versão anterior"
        assert resumo["bloqueio"]["motivo"] == "revalidar"
        assert resumo["versaoVigente"] == futura
    finally:
        with engine.begin() as conexao:
            conexao.execute(text("DELETE FROM termos WHERE versao = :futura"), {"futura": futura})
            conexao.execute(
                text("UPDATE termos SET vigente = true WHERE tipo = 'cliente' AND versao = :anterior"),
                {"anterior": anterior},
            )


def test_termos_expostos_por_versao(cliente_http: TestClient, versao_vigente):
    vigente = cliente_http.get("/api/v1/termos/cliente").json()
    assert vigente["versao"] == versao_vigente("cliente") and vigente["vigente"] is True
    assert any(secao["destaque"] for secao in vigente["secoes"])

    # A 0.9 continua publicada e fora de vigência: é o documento que clientes anteriores
    # leram, e apagá-la quebraria o vínculo exigido pelo art. 37.
    antigo = cliente_http.get("/api/v1/termos/cliente/0.9").json()
    assert antigo["versao"] == "0.9" and antigo["vigente"] is False
    assert cliente_http.get("/api/v1/termos/cliente/9.9").status_code == 404
    assert (
        cliente_http.get("/api/v1/termos/profissional").json()["versao"]
        == versao_vigente("profissional")
    )


@pytest.mark.parametrize("decisao", ["aceito", "recusado"])
def test_forma_de_obtencao_invalida(cliente_http: TestClient, conta, decisao):
    cabecalhos, _ = conta()
    cliente = novo_cliente(cliente_http, cabecalhos)
    resposta = registrar(
        cliente_http, cabecalhos, cliente["id"], decisao=decisao, formaObtencao="telepatia"
    )
    assert resposta.status_code == 422
