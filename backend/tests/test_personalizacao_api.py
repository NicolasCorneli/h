"""Rotas da etapa "Estilo e cor" com o provedor local (sem rede): prévia do plano,
geração com o pedido descrito e envio único.

O provedor local não é IA: a imagem sai recolorida e com aviso. O que se testa aqui é o
contrato e as regras do servidor; o provedor real é exercitado contra o servidor de
mentira em `test_simulacao_com_mock_ia.py`.
"""

from __future__ import annotations

import time
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.fabricas import arquivo_de_foto

ACEITE = {
    "decisao": "aceito",
    "formaObtencao": "tela_dispositivo",
    "confirmadoPor": "Marina Alves",
    "observacao": "",
}


def cliente_com_aceite(cliente_http: TestClient, cabecalhos) -> dict:
    cliente = cliente_http.post(
        "/api/v1/clientes", headers=cabecalhos, json={"nome": "Marina Alves", "telefone": "1"}
    ).json()
    cliente_http.post(f"/api/v1/clientes/{cliente['id']}/consentimentos", headers=cabecalhos, json=ACEITE)
    return cliente


def enviar(cliente_http: TestClient, cabecalhos, cliente_id: str, **campos):
    dados = {"clienteId": cliente_id, "corte": "Chanel", "cor": "Loiro", "observacoes": "", **campos}
    return cliente_http.post("/api/v1/simulacoes", headers=cabecalhos, data=dados, files=arquivo_de_foto())


def aguardar(cliente_http: TestClient, cabecalhos, simulacao_id: str) -> dict:
    for _ in range(60):
        estado = cliente_http.get(f"/api/v1/simulacoes/{simulacao_id}", headers=cabecalhos).json()
        if estado["status"] != "processando":
            return estado
        time.sleep(0.1)
    raise AssertionError("a simulação ficou presa em processando")


# --- Prévia ----------------------------------------------------------------


def test_previa_do_plano_por_tipo_de_pedido(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()

    def plano(**pedido):
        return cliente_http.post("/api/v1/simulacoes/plano", headers=cabecalhos, json=pedido)

    opcoes = plano(corte="Pixie", cor="Ruivo").json()
    assert opcoes["provedor"] == "fake"
    assert opcoes["modo"] == "opcoes"
    assert opcoes["modelo"] == "flux-kontext-apps/change-haircut"
    assert opcoes["instrucao"] == "haircut=Pixie Cut; hair_color=Copper"

    livre = plano(corte="Bob na altura do queixo", manterCor=True).json()
    assert livre["modo"] == "descricao"
    assert livre["modelo"] == "black-forest-labs/flux-kontext-pro"
    assert "Bob na altura do queixo" in livre["instrucao"]
    assert livre["cor"] == "Cor atual"

    feminino = plano(corte="Pixie", cor="Ruivo", genero="female").json()
    assert feminino["instrucao"] == "haircut=Pixie Cut; hair_color=Copper; gender=female"
    invalido = plano(corte="Pixie", cor="Ruivo", genero="feminino")
    assert invalido.status_code == 422
    assert invalido.json()["erro"]["codigo"] == "genero_invalido"

    vazio = plano(manterCorte=True, manterCor=True)
    assert vazio.status_code == 422
    assert vazio.json()["erro"]["codigo"] == "pedido_vazio"


# --- Geração com o pedido novo ----------------------------------------------


def test_simulacao_com_descricao_livre_grava_o_pedido(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    criada = enviar(
        cliente_http,
        cabecalhos,
        cliente["id"],
        corte="Bob na altura do queixo, com camadas suaves",
        cor="",
        manterCor="true",
    )
    assert criada.status_code == 202, criada.text
    final = aguardar(cliente_http, cabecalhos, criada.json()["id"])
    assert final["status"] == "concluida"
    assert final["parametros"]["estilo"] == "Bob na altura do queixo, com camadas suaves"
    assert final["parametros"]["cor"] == "Cor atual"
    assert "Bob na altura do queixo" in final["instrucaoIa"]


# --- Envio único ----------------------------------------------------------


def test_mesma_chave_de_envio_devolve_a_mesma_simulacao(cliente_http: TestClient, conta):
    """Toque duplo ou reenvio depois de a rede cair: uma geração, não duas."""
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    chave = str(uuid.uuid4())
    primeira = enviar(cliente_http, cabecalhos, cliente["id"], chaveEnvio=chave)
    segunda = enviar(cliente_http, cabecalhos, cliente["id"], chaveEnvio=chave)
    assert primeira.status_code == segunda.status_code == 202
    assert primeira.json()["id"] == segunda.json()["id"]
    lista = cliente_http.get(f"/api/v1/simulacoes?clienteId={cliente['id']}", headers=cabecalhos).json()
    assert len(lista) == 1

    outra = enviar(cliente_http, cabecalhos, cliente["id"], chaveEnvio=str(uuid.uuid4()))
    assert outra.json()["id"] != primeira.json()["id"]


def test_reenvio_nao_conta_na_cota(cliente_http: TestClient, conta, monkeypatch):
    from app.core import config as modulo_config

    monkeypatch.setenv("SIMULACAO_MAX_POR_HORA", "1")
    modulo_config.obter_config.cache_clear()
    try:
        cabecalhos, _ = conta()
        cliente = cliente_com_aceite(cliente_http, cabecalhos)
        chave = str(uuid.uuid4())
        assert enviar(cliente_http, cabecalhos, cliente["id"], chaveEnvio=chave).status_code == 202
        # Com a cota esgotada, o mesmo envio ainda devolve a simulação já criada...
        assert enviar(cliente_http, cabecalhos, cliente["id"], chaveEnvio=chave).status_code == 202
        # ...e um envio novo é recusado.
        nova = enviar(cliente_http, cabecalhos, cliente["id"], chaveEnvio=str(uuid.uuid4()))
        assert nova.status_code == 429
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()


def test_chave_de_outra_conta_nao_devolve_simulacao_alheia(cliente_http: TestClient, conta):
    cabecalhos_a, _ = conta()
    cabecalhos_b, _ = conta()
    cliente_a = cliente_com_aceite(cliente_http, cabecalhos_a)
    cliente_b = cliente_com_aceite(cliente_http, cabecalhos_b)
    chave = str(uuid.uuid4())
    da_a = enviar(cliente_http, cabecalhos_a, cliente_a["id"], chaveEnvio=chave).json()
    da_b = enviar(cliente_http, cabecalhos_b, cliente_b["id"], chaveEnvio=chave).json()
    assert da_a["id"] != da_b["id"]
    assert da_b["clienteId"] == cliente_b["id"]


def test_chave_reutilizada_para_outro_cliente_e_recusada(cliente_http: TestClient, conta):
    cabecalhos, _ = conta()
    um = cliente_com_aceite(cliente_http, cabecalhos)
    outro = cliente_com_aceite(cliente_http, cabecalhos)
    chave = str(uuid.uuid4())
    assert enviar(cliente_http, cabecalhos, um["id"], chaveEnvio=chave).status_code == 202
    resposta = enviar(cliente_http, cabecalhos, outro["id"], chaveEnvio=chave)
    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "chave_reutilizada"


def test_reenvio_nao_agenda_outro_processamento(cliente_http: TestClient, conta, monkeypatch):
    """Com a primeira geração ainda em andamento, o reenvio não pode disparar outra.

    No TestClient a tarefa em segundo plano termina antes da segunda requisição, e o
    processamento repetido sairia sem efeito: por isso o teste conta as chamadas.
    """
    from app.services import simulacao as servico

    agendadas: list[str] = []
    monkeypatch.setattr(servico, "processar", lambda simulacao_id, **_: agendadas.append(str(simulacao_id)))
    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    chave = str(uuid.uuid4())
    primeira = enviar(cliente_http, cabecalhos, cliente["id"], chaveEnvio=chave)
    segunda = enviar(cliente_http, cabecalhos, cliente["id"], chaveEnvio=chave)
    assert primeira.json()["id"] == segunda.json()["id"]
    assert segunda.json()["status"] == "processando"
    assert agendadas == [primeira.json()["id"]], "o reenvio agendou outra geração paga"


# --- Migration ------------------------------------------------------------


def test_volta_da_migration_recusa_cortar_descricao(cliente_http: TestClient, conta):
    """Descrição acima de 60 caracteres não cabe na coluna antiga: a volta se recusa."""
    from alembic import command
    from alembic.config import Config

    from tests.conftest import RAIZ

    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    longa = "Cabelo longo com franja cortininha e camadas ao redor do rosto, sem tirar comprimento"
    criada = enviar(cliente_http, cabecalhos, cliente["id"], corte=longa)
    assert criada.status_code == 202
    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    with pytest.raises(RuntimeError, match="acima de 60 caracteres"):
        command.downgrade(configuracao, "a3e7b5c90d14")
    # Nada foi desfeito: a descrição continua inteira.
    final = cliente_http.get(f"/api/v1/simulacoes/{criada.json()['id']}", headers=cabecalhos).json()
    assert final["parametros"]["estilo"] == longa


def test_migration_vai_e_volta_sem_descricoes_longas():
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    from app.db.session import engine
    from tests.conftest import RAIZ

    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    command.downgrade(configuracao, "a3e7b5c90d14")
    colunas = {c["name"]: c for c in inspect(engine).get_columns("simulacoes")}
    assert "chave_envio" not in colunas and colunas["estilo"]["type"].length == 60
    command.upgrade(configuracao, "head")
    colunas = {c["name"]: c for c in inspect(engine).get_columns("simulacoes")}
    assert {"instrucao_ia", "chave_envio"} <= set(colunas)
    assert "usou_referencia" not in colunas
    assert colunas["estilo"]["type"].length == 300


def test_volta_da_remocao_da_referencia_recria_a_coluna_pelo_que_foi_gravado(cliente_http: TestClient, conta):
    """A coluna `usou_referencia` saiu; a volta a recria a partir de `instrucao_ia`."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from app.db.session import engine
    from tests.conftest import RAIZ

    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    com_referencia = aguardar(cliente_http, cabecalhos, enviar(cliente_http, cabecalhos, cliente["id"]).json()["id"])
    sem_referencia = aguardar(cliente_http, cabecalhos, enviar(cliente_http, cabecalhos, cliente["id"]).json()["id"])
    with engine.begin() as conexao:
        # Instrução como a que o modelo de duas imagens recebia antes da remoção.
        conexao.execute(
            text("UPDATE simulacoes SET instrucao_ia = :instrucao WHERE id = :id"),
            {
                "id": com_referencia["id"],
                "instrucao": "The first image is the client. The second image is only a hairstyle reference.",
            },
        )
    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "migrations"))
    command.downgrade(configuracao, "b9d4e1f27c35")
    try:
        with engine.connect() as conexao:
            marcadas = dict(conexao.execute(text("SELECT id::text, usou_referencia FROM simulacoes")).all())
        assert marcadas[com_referencia["id"]] is True
        assert marcadas[sem_referencia["id"]] is False
    finally:
        command.upgrade(configuracao, "head")


def test_rotas_e_campos_removidos_nao_existem(cliente_http: TestClient):
    """Foto de referência e pedido por voz saíram do sistema: nada deles fica publicado."""
    contrato = cliente_http.get("/openapi.json").json()
    assert not [rota for rota in contrato["paths"] if "transcricao" in rota or "recursos" in rota]
    formulario = next(
        esquema
        for nome, esquema in contrato["components"]["schemas"].items()
        if nome.startswith("Body_criar")
    )
    assert "referencia" not in formulario["properties"]
    assert set(formulario["properties"]) >= {"clienteId", "foto", "corte", "cor", "manterCorte", "manterCor"}


def test_sem_chave_responde_o_motivo_e_nao_deixa_foto_orfa(cliente_http: TestClient, conta, monkeypatch):
    """No código anterior: 500 genérico, e a foto ficava no storage sem registro no banco."""
    from app.core import config as modulo_config

    cabecalhos, _ = conta()
    cliente = cliente_com_aceite(cliente_http, cabecalhos)
    pasta = modulo_config.obter_config().storage_dir
    antes = {p for p in pasta.rglob("*") if p.is_file()} if pasta.exists() else set()
    monkeypatch.setenv("AI_PROVIDER", "replicate")
    monkeypatch.setenv("AI_API_KEY", "")
    modulo_config.obter_config.cache_clear()
    try:
        resposta = enviar(cliente_http, cabecalhos, cliente["id"])
    finally:
        monkeypatch.undo()
        modulo_config.obter_config.cache_clear()
    assert resposta.status_code == 502
    assert resposta.json()["erro"]["codigo"] == "credencial_ausente"
    depois = {p for p in pasta.rglob("*") if p.is_file()} if pasta.exists() else set()
    assert depois == antes, "a foto ficou gravada sem simulação"
    assert cliente_http.get(f"/api/v1/simulacoes?clienteId={cliente['id']}", headers=cabecalhos).json() == []
